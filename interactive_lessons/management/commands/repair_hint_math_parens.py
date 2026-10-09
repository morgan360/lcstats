"""Repair question hints whose maths the KaTeX sanitizer broke.

Before sanitizer 1.0.9, Question.save() ran any hint containing "(\\" or "[\\"
through sanitize_katex without protecting $...$ maths, so its wrapper for
bare "(\\sigma)" fired inside formulas: \\left(\\frac{a}{b}\\right) became
\\left\\(\\frac{a}{b}\\right\\), \\ln(x) became \\ln\\(x\\), P(A) became P\\(A\\).
KaTeX shows those as raw code. On production on 2026-10-09 that was 34 hints
across Differential Calculus, Indices and Logs, Probability and both Trig
topics.

The repair turns \\( back into ( and \\) into ), inside $...$ maths only, so
genuine \\(...\\) delimiters elsewhere in a hint are untouched. It writes with
QuerySet.update(), not save(), so the sanitizer does not run again over the
rest of the hint. Idempotent: a repaired hint has nothing left to match.
"""
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from interactive_lessons.models import Question

DOLLAR_MATH = re.compile(r"(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)")


def repair(text):
    """The text with \\( and \\) unescaped inside $...$ maths."""
    def fix(m):
        return "$" + m.group(1).replace("\\(", "(").replace("\\)", ")") + "$"
    return DOLLAR_MATH.sub(fix, text)


class Command(BaseCommand):
    help = "Unescape \\( and \\) that the sanitizer put inside $...$ maths in hints"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would change without writing anything")

    def handle(self, *args, **options):
        changed = 0
        with transaction.atomic():
            for q in Question.objects.exclude(hint="").exclude(hint=None).select_related(
                    "topic", "section").order_by("topic__name", "section__order", "order"):
                fixed = repair(q.hint)
                if fixed == q.hint:
                    continue
                changed += 1
                where = f"{q.topic.name} / {q.section.name if q.section else '-'} / Q{q.order}"
                self.stdout.write(f"  {where}")
                if not options["dry_run"]:
                    Question.objects.filter(pk=q.pk).update(hint=fixed)
        verb = "Would repair" if options["dry_run"] else "Repaired"
        self.stdout.write(self.style.SUCCESS(f"\n{verb} {changed} hints."))
