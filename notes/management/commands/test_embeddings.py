import json
import numpy as np
from django.core.management.base import BaseCommand
from openai import OpenAI
from notes.models import Note
from notes.utils import get_query_embedding, search_similar

client = OpenAI()

TEST_QUERIES = {
    "descriptive-statistics": [
        "definition of mean",
        "definition of median",
        "definition of mode",
        "standard deviation",
        "histogram",
        "scatter plot",
    ],
    "inferential-statistics": [
        "confidence interval",
        "hypothesis test",
        "t-test",
        "z-score",
        "p-value",
        "sampling distribution",
    ],
}


class Command(BaseCommand):
    help = "Test note embeddings by running queries and reporting similarity scores."

    def add_arguments(self, parser):
        parser.add_argument(
            "topic",
            nargs="?",
            default=None,
            help="Optional topic slug (e.g. 'descriptive-statistics') to restrict testing.",
        )
        parser.add_argument(
            "--top",
            type=int,
            default=3,
            help="How many top matches to display per query (default 3).",
        )
        parser.add_argument(
            "--prompt",
            type=str,
            help="Custom query string to test directly "
                 "(e.g. --prompt 'explain how to calculate the mean').",
        )

    def handle(self, *args, **options):
        topic = options["topic"]
        top_n = options["top"]
        custom_prompt = options.get("prompt")

        # --- Handle direct prompt testing ---
        if custom_prompt:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n🧠 Custom query: {custom_prompt}"))
            results = search_similar(custom_prompt, topic=topic, top_n=top_n)

            if not results:
                self.stdout.write("⚠️  No matches found.\n")
                return

            for score, note in results:
                color = self._color_for_score(score)
                self.stdout.write(f"{color}  →  {note.title}  ({score:.3f})")
            return  # Stop here for single prompt tests

        # --- Otherwise use predefined test queries ---
        if topic:
            queries = TEST_QUERIES.get(topic, [])
            if not queries:
                self.stdout.write(self.style.WARNING(f"No test queries defined for topic '{topic}'"))
                return
        else:
            # Flatten all lists if no specific topic
            queries = sum(TEST_QUERIES.values(), [])

        if not Note.objects.exists():
            self.stdout.write(self.style.ERROR("No notes found in database."))
            return

        self.stdout.write(self.style.SUCCESS(f"\n🔍 Testing embeddings for topic: {topic or 'ALL'}\n"))

        for q in queries:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n🧠 Query: {q}"))
            results = search_similar(q, topic=topic, top_n=top_n)

            if not results:
                self.stdout.write("⚠️  No matches found.\n")
                continue

            for score, note in results:
                color = self._color_for_score(score)
                self.stdout.write(f"{color}  →  {note.title}  ({score:.3f})")

    # --- Helper: colour output based on score ---
    def _color_for_score(self, score):
        if score >= 0.8:
            return self.style.SUCCESS("  ✅ High")
        elif score >= 0.6:
            return self.style.WARNING("  ⚠️  Medium")
        else:
            return self.style.ERROR("  ❌ Low")
