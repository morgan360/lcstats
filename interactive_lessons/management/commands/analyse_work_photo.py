"""Probe for the photograph-your-working feature. Throwaway except for the prompt.

Runs the vision analysis against a photo on disk, so the prompt can be tried on
real handwriting before any of the upload, storage or QR machinery exists.

    python manage.py analyse_work_photo ~/Desktop/copy1.jpg --part 42
    python manage.py analyse_work_photo ~/Desktop/graph.jpg --exam-part 87
    python manage.py analyse_work_photo ~/Desktop/messy.jpg --part 42 --raw

What to look for, on five or so photos taken in ordinary light:
  - is the transcription faithful, including the student's own errors?
  - on a right-method-wrong-arithmetic page, does it find the slip and name
    the line, rather than just saying it is wrong?
  - on a hand-drawn graph, does it say something specific about axes, shape,
    intercepts and asymptotes?
  - on a deliberately bad photo, does it admit it cannot read, or invent?
If those hold it is worth building; if not, stop here.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from exam_papers.models import ExamQuestionPart
from exam_papers.services.work_analysis import analyse_student_work
from interactive_lessons.models import QuestionPart
from students.services.image_intake import ImageIntakeError, encode_path_for_api

BAR = "─" * 72


class Command(BaseCommand):
    help = "Analyse a photo of handwritten working against a question part (probe)."

    def add_arguments(self, parser):
        parser.add_argument("photo", help="Path to a photo of handwritten working")
        parser.add_argument("--part", type=int, help="interactive_lessons QuestionPart id")
        parser.add_argument("--exam-part", type=int, help="exam_papers ExamQuestionPart id")
        parser.add_argument("--raw", action="store_true", help="Dump the unparsed response")
        parser.add_argument(
            "--no-context", action="store_true",
            help="Withhold the answer and marking scheme, to see the analysis unaided",
        )

    def handle(self, *args, **options):
        path = Path(options["photo"]).expanduser()
        if not path.exists():
            raise CommandError(f"No such photo: {path}")
        if not (options["part"] or options["exam_part"]):
            raise CommandError("Give either --part or --exam-part")

        part, kwargs = self._resolve_part(options)

        try:
            image_b64 = encode_path_for_api(path)
        except ImageIntakeError as e:
            raise CommandError(str(e))

        self.stdout.write(f"Photo:    {path.name}")
        self.stdout.write(f"Question: {kwargs['question_prompt'][:100]}")
        self.stdout.write(self.style.WARNING("Calling the vision model...\n"))

        try:
            result = analyse_student_work(image_b64, **kwargs)
        except Exception as e:
            raise CommandError(f"Analysis failed: {e!r}")

        if options["raw"]:
            self.stdout.write(json.dumps(result, indent=2, default=str))
            return

        self._report(result)

    def _resolve_part(self, options):
        """Load the part and assemble the context the analyser takes."""
        bare = options["no_context"]

        if options["part"]:
            part = QuestionPart.objects.filter(pk=options["part"]).select_related("question").first()
            if not part:
                raise CommandError(f"No QuestionPart with id {options['part']}")
            return part, {
                "question_prompt": part.prompt or part.question.text,
                "part_label": part.label or "",
                "question_image": None if bare else (part.image or part.question.image),
                "marking_scheme_image": None,
                "expected_answer": None if bare else (part.answer or part.solution),
            }

        part = ExamQuestionPart.objects.filter(pk=options["exam_part"]).select_related("question").first()
        if not part:
            raise CommandError(f"No ExamQuestionPart with id {options['exam_part']}")
        # Exam parts carry no question text -- the question exists only as an
        # image -- so the model has to read it from the picture. Withholding
        # that image under --no-context leaves it nothing to work from, so the
        # flag only suppresses the marking scheme here.
        return part, {
            "question_prompt": "Shown in the question image below.",
            "part_label": part.label or "",
            "question_image": getattr(part.question, "image", None),
            "marking_scheme_image": None if bare else part.solution_image,
            "expected_answer": None,
        }

    def _report(self, result):
        out, style = self.stdout, self.style

        readable = result.get("readable", True)
        has_working = result.get("has_working", True)
        confidence = result.get("confidence", "?")
        flag = style.SUCCESS if readable and has_working and confidence == "high" else style.WARNING
        out.write(flag(f"readable={readable}  has_working={has_working}  "
                       f"confidence={confidence}  diagram={result.get('has_diagram')}"))

        out.write(f"\n{BAR}\nWHAT IT READ\n{BAR}")
        out.write(result.get("transcription", "") or "(nothing)")

        steps = result.get("steps") or []
        if steps:
            out.write(f"\n{BAR}\nSTEPS\n{BAR}")
            marks = {"correct": "✓", "slip": "~", "wrong": "✗", "unclear": "?"}
            for s in steps:
                verdict = s.get("verdict", "unclear")
                colour = {
                    "correct": style.SUCCESS, "slip": style.WARNING,
                    "wrong": style.ERROR,
                }.get(verdict, style.NOTICE)
                out.write(colour(f"  {marks.get(verdict, '?')} {s.get('step', '')}"))
                if s.get("comment"):
                    out.write(f"      {s['comment']}")

        for heading, key in (("METHOD", "method_feedback"),
                             ("GRAPH", "diagram_feedback"),
                             ("NEXT STEP", "next_step")):
            if result.get(key):
                out.write(f"\n{BAR}\n{heading}\n{BAR}")
                out.write(result[key])

        if result.get("strengths"):
            out.write(f"\n{BAR}\nSTRENGTHS\n{BAR}")
            for s in result["strengths"]:
                out.write(f"  • {s}")

        if result.get("final_answer"):
            out.write(f"\nFinal answer read as: {result['final_answer']}")

        usage = result.get("usage", {})
        out.write(style.NOTICE(
            f"\n{result.get('model_used')}  "
            f"{usage.get('prompt_tokens', 0)} prompt + "
            f"{usage.get('completion_tokens', 0)} completion tokens"
        ))
