"""Run the homework-check pipeline from a laptop, against real files.

This is the go/no-go probe. It exists to answer, before any UI is built,
whether the model can actually do the job on real handwriting:

  - does it read the question numbers off a student's page correctly?
  - does it find those questions in the solutions PDF?
  - **does it refuse to invent an answer for a question the PDF does not
    cover?** This is the one that matters. A confident wrong answer printed
    on a sheet and handed to a student is the worst thing this tool can do.
  - does it tell a sign slip apart from the wrong method?

Deliberately model-free: it takes a PDF path and photo paths, renders and
encodes them in memory, and never touches the database. So it runs before the
migrations exist, and it can be pointed at anything.

    python manage.py check_homework_photos \\
        --pdf ~/solutions/week3.pdf --photos a.jpg b.jpg --exercise "Ex 5A"

    # only pages 3-4 of the solutions, and show the whole prompt
    python manage.py check_homework_photos --pdf s.pdf --photos a.jpg \\
        --pages 3-4 --show-prompt
"""
import json

from django.core.management.base import BaseCommand, CommandError

from exam_papers.utils import extract_pdf_pages_as_images
from homework_check.services import assembly
from homework_check.services.check_analysis import analyse_chunk, build_prompt
from homework_check.services.solution_pages import RENDER_DPI, parse_page_range
from homework_check.services.summarise import summarise
from students.services.image_intake import ImageIntakeError, encode_path_for_api

VERDICT_MARK = {
    "correct": "OK ",
    "slip": "~  ",
    "wrong": "X  ",
    "incomplete": "..",
    "unclear": "?  ",
}


class Command(BaseCommand):
    help = "Probe the homework-check pipeline against a solutions PDF and photos."

    def add_arguments(self, parser):
        parser.add_argument("--pdf", required=True,
                            help="Path to the worked solutions PDF")
        parser.add_argument("--photos", nargs="+", required=True,
                            help="Paths to photos of the student's copy")
        parser.add_argument("--exercise", default="Homework exercise",
                            help="What the teacher called this exercise")
        parser.add_argument("--pages", default="",
                            help='Solution pages to use, e.g. "3-4". Blank = all')
        parser.add_argument("--chunk-size", type=int, default=4,
                            help="Photos per vision call (default 4)")
        parser.add_argument("--show-prompt", action="store_true",
                            help="Print the prompt and exit without calling the API")
        parser.add_argument("--json", action="store_true",
                            help="Print the raw assembled JSON as well")
        parser.add_argument("--no-summary", action="store_true",
                            help="Skip the closing-note call")

    def handle(self, *args, **options):
        photo_paths = options["photos"]
        chunk_size = max(1, options["chunk_size"])

        self.stdout.write(f"Rendering {options['pdf']} at {RENDER_DPI} dpi…")
        try:
            rendered = extract_pdf_pages_as_images(options["pdf"], dpi=RENDER_DPI)
        except Exception as e:
            raise CommandError(f"Could not read the PDF: {e}")

        wanted = set(parse_page_range(options["pages"], len(rendered)))
        pages = [(n, data) for n, data in rendered if n in wanted]
        page_numbers = [n for n, _ in pages]
        self.stdout.write(
            f"  {len(rendered)} page(s) in the PDF, using {page_numbers}"
        )

        self.stdout.write("Encoding solution pages…")
        page_b64s = [self._encode(io_bytes) for _, io_bytes in pages]

        self.stdout.write(f"Encoding {len(photo_paths)} photo(s)…")
        photo_b64s = []
        for path in photo_paths:
            try:
                photo_b64s.append(self._encode_path(path))
            except ImageIntakeError as e:
                raise CommandError(f"{path}: {e}")

        if options["show_prompt"]:
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(build_prompt(options["exercise"], page_numbers))
            return

        chunks = []
        total = {"prompt_tokens": 0, "completion_tokens": 0, "cached_tokens": 0}
        for start in range(0, len(photo_b64s), chunk_size):
            batch = photo_b64s[start:start + chunk_size]
            label = f"photos {start + 1}-{start + len(batch)}"
            self.stdout.write(f"Analysing {label} ({len(batch)} + "
                              f"{len(page_b64s)} images)…")
            result = analyse_chunk(
                batch, page_b64s, options["exercise"],
                page_numbers=page_numbers, chunk_label=label,
                # Mirrors what the runner sends, so the probe measures the
                # caching the live path actually gets.
                cache_key=f"hwcheck-probe-{options['pages'] or 'all'}",
            )
            chunks.append(result)
            for key in total:
                total[key] += result["usage"].get(key, 0)
            self.stdout.write(
                f"  tokens {result['usage']['prompt_tokens']} in "
                f"({result['usage']['cached_tokens']} cached) / "
                f"{result['usage']['completion_tokens']} out"
            )

        report = assembly.assemble(chunks)

        if not options["no_summary"] and report["questions"]:
            self.stdout.write("Writing the closing note…")
            try:
                text, usage = summarise(options["exercise"], report["questions"])
                report["summary"] = text
                for key in total:
                    total[key] += usage.get(key, 0)
            except Exception as e:
                self.stderr.write(f"  summary call failed ({e}); using fallback")
                report["summary"] = assembly.fallback_summary(
                    report["questions"], report["counts"])
        else:
            report["summary"] = assembly.fallback_summary(
                report["questions"], report["counts"])

        self._render(report, chunks, total, options)

    def _encode(self, png_bytes):
        import io
        return encode_path_for_api(io.BytesIO(png_bytes))

    def _encode_path(self, path):
        with open(path, "rb") as fh:
            return encode_path_for_api(fh)

    def _render(self, report, chunks, total, options):
        out = self.stdout
        out.write("\n" + "=" * 70)
        out.write(f"  {options['exercise']}")
        out.write("=" * 70)

        counts = report["counts"]
        out.write(
            f"\nRead: {'yes' if report['readable'] else 'NO'}   "
            f"confidence: {report['confidence'] or '-'}   "
            f"model: {chunks[0]['model_used'] if chunks else '-'}"
        )

        rating = report["rating"] or "WITHHELD"
        out.write(f"Rating: {rating.upper()}"
                  + (f"  ({report['rating_reason']})" if report["rating_reason"] else ""))
        out.write(
            f"Questions: {counts['total']}  "
            f"correct {counts['correct']}, slip {counts['slip']}, "
            f"wrong {counts['wrong']}, incomplete {counts['incomplete']}, "
            f"unclear {counts['unclear']}"
        )
        if counts["not_in_solutions"]:
            out.write(self.style.WARNING(
                f"  {counts['not_in_solutions']} question(s) NOT found in the "
                "solutions — check these refused to invent an answer"
            ))

        out.write("\n" + "-" * 70)
        for q in report["questions"]:
            mark = VERDICT_MARK.get(q["verdict"], "?  ")
            out.write(f"{mark} {q['label']}")
            if q["student_answer"]:
                out.write(f"      theirs:  {q['student_answer']}")
            if q["correct_answer"]:
                out.write(f"      correct: {q['correct_answer']}")
            elif not q["found_in_solutions"]:
                out.write("      correct: (not in the solutions supplied)")
            if q["comment"]:
                out.write(f"      {q['comment']}")
            out.write("")

        if report["has_diagram"] and report["diagram_feedback"]:
            out.write("-" * 70)
            out.write("Diagram: " + report["diagram_feedback"] + "\n")

        if report["notes"]:
            out.write("-" * 70)
            for note in report["notes"]:
                out.write("Note: " + note)
            out.write("")

        out.write("-" * 70)
        out.write("Closing note: " + report.get("summary", ""))

        out.write("\n" + "-" * 70)
        out.write(f"Tokens: {total['prompt_tokens']} in "
                  f"({total['cached_tokens']} served from cache) / "
                  f"{total['completion_tokens']} out across "
                  f"{len(chunks)} vision call(s)")

        if options["json"]:
            out.write("\n" + json.dumps(report, indent=2))
