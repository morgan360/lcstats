"""Move three exponential/log questions out of Functions > Composite Functions.

They define an f and a g but never compose them: part (i) evaluates an
exponential, part (ii) solves a log equation. They belong in Indices and Logs,
in their own "Exponential & Log Equations" section, and this moves them there
whole, so any attempts on them move too (none on production as of 2026-10-09).

On the way it fixes two faults found while checking them:
- ln(5x) = 4.2 was stored as 13.29; x = e^4.2 / 5 = 13.337..., so 13.34
  (the worked solution already said 13.34).
- One hint showed \\ln\\(x\\) as raw code; it is reworded (see CUBE_ROOT_HINT).

Idempotent and keyed on content, not ids: a question is one of the three if
its first part asks for f(...) "in the form a x 10^n". Run it before
add_functions_questions, which writes new questions into the positions these
leave and refuses to run while they are still there.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max

from interactive_lessons.models import Question, Section, Topic

FROM_TOPIC, FROM_SECTION = "functions", "Composite Functions"

# The old hint wrote \ln(\sqrt[n]{x}), and Question.save() runs any hint
# containing "(\" through sanitize_katex, which turns \ln(x) into \ln\(x\)
# and breaks it again. This wording says the same with no "(\" in it.
CUBE_ROOT_HINT = (
    r"For exponential functions, $e^{ax}$ can be evaluated directly using a "
    r"calculator. A root inside a log is a power: $\ln \sqrt[n]{x} = "
    r"\ln x^{1/n} = \frac{1}{n}\ln x$. So $\ln \sqrt[3]{x} = k$ becomes "
    r"$\frac{1}{3}\ln x = k$, giving $\ln x = 3k$ and $x = e^{3k}$."
)
TO_TOPIC, TO_SECTION, TO_ORDER = "indices-and-logs", "Exponential & Log Equations", 9


def misfiled(section):
    """The exp/log questions sitting in this section, in their order."""
    return [q for q in Question.objects.filter(section=section).order_by("order")
            if is_exp_log(q)]


def is_exp_log(question):
    first = question.parts.order_by("order").first()
    return bool(first) and "Find the value of $f(" in first.prompt and "10^n" in first.prompt


class Command(BaseCommand):
    help = "Move the exponential/log questions from Composite Functions to Indices and Logs"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would change without writing anything")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        source = Section.objects.filter(topic__slug=FROM_TOPIC, name=FROM_SECTION).first()
        questions = misfiled(source) if source else []
        if not questions:
            self.stdout.write("Nothing to move: Composite Functions has no exp/log questions.")
            return

        with transaction.atomic():
            target_topic = Topic.objects.get(slug=TO_TOPIC)
            target, made = Section.objects.get_or_create(
                topic=target_topic, name=TO_SECTION, defaults={"order": TO_ORDER})
            self.stdout.write(f'{"Created" if made else "Found"} section "{target.name}" '
                              f'in {target_topic.name}')
            start = (Question.objects.filter(section=target).aggregate(m=Max("order"))["m"] or 0)

            for n, q in enumerate(questions, start=1):
                old = q.order
                q.topic, q.section, q.order = target_topic, target, start + n
                if "\\ln\\(x\\)" in (q.hint or ""):
                    q.hint = CUBE_ROOT_HINT
                q.save()
                fixed = q.parts.filter(answer="13.29").update(answer="13.34")
                self.stdout.write(f"  moved question {old} -> {target.name} {q.order}"
                                  f'{" (answer 13.29 -> 13.34)" if fixed else ""}')

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'\n{"Would move" if dry_run else "Moved"} {len(questions)} questions.'))
