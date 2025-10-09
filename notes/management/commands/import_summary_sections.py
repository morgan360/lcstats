# notes/management/commands/import_summary_sections.py
import re
import fitz  # PyMuPDF
from django.core.management.base import BaseCommand
from openai import OpenAI
from notes.models import Note

client = OpenAI()

class Command(BaseCommand):
    help = "Import Stats Summary into Notes by section (instead of page)"

    def add_arguments(self, parser):
        parser.add_argument("pdf_path", type=str)
        parser.add_argument("--topic", type=str, default="Statistics Summary")

    def handle(self, *args, **options):
        pdf_path = options["pdf_path"]
        topic = options["topic"]

        # ✅ 1. Open PDF
        doc = fitz.open(pdf_path)

        # ✅ 2. Extract structured text, keeping layout & math symbols
        full_text = ""
        for page in doc:
            blocks = page.get_text("blocks")  # list of text blocks
            for block in blocks:
                block_text = block[4]

                # Replace common math & symbol characters with LaTeX equivalents
                block_text = (
                    block_text.replace("²", "^2")
                              .replace("³", "^3")
                              .replace("±", r"$\pm$")
                              .replace("≤", r"$\leq$")
                              .replace("≥", r"$\geq$")
                              .replace("×", r"$\times$")
                              .replace("÷", r"$\div$")
                              .replace("μ", r"$\mu$")
                              .replace("σ", r"$\sigma$")
                              .replace("Σ", r"$\Sigma$")
                )

                full_text += block_text + "\n\n"

        # ✅ 3. Clean newlines
        full_text = re.sub(r"\n+", "\n", full_text).strip()

        # ✅ 4. Split text by numbered sections (1), 2), 3) …)
        sections = re.split(r"\n(?=\d+\))", full_text)
        print(f"Found {len(sections)} sections")

        # ✅ 5. Create Note entries
        for sec in sections:
            lines = sec.strip().splitlines()
            if not lines:
                continue

            title_line = lines[0]
            body = "\n".join(lines[1:]).strip()

            title = re.sub(r"^\d+\)\s*", "", title_line).strip(" :")

            if len(body) < 50:
                continue

            embedding = client.embeddings.create(
                model="text-embedding-3-large",
                input=body
            ).data[0].embedding

            Note.objects.update_or_create(
                title=f"{topic} - {title}",
                topic=topic,
                defaults={"content": body, "embedding": embedding},
            )

        self.stdout.write(self.style.SUCCESS(f"✅ Imported {len(sections)} sections of {topic}"))
