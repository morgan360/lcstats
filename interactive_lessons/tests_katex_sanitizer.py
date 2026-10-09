"""The KaTeX sanitizer must not touch maths inside $...$.

Before 1.0.9 it did: saving a hint turned \\left(\\frac{a}{b}\\right) into
\\left\\(...\\right\\) and \\ln(x) into \\ln\\(x\\), which KaTeX shows as raw
code. 34 hints on production had been damaged that way.
"""
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from interactive_lessons.management.commands.repair_hint_math_parens import repair
from interactive_lessons.models import Question, Topic
from interactive_lessons.utils.katex_sanitizer import sanitize_katex


class DollarMathIsProtectedTests(SimpleTestCase):

    def test_brackets_inside_dollar_maths_are_left_alone(self):
        for text in [
            r"Law 9: $\left(\frac{a}{b}\right)^p = \frac{a^p}{b^p}$",
            r"Use $\frac{d}{dx}[\ln(x)] = \frac{1}{x}$ here",
            r"$P(\text{at least one}) = 1 - P(\text{none})$",
            r"$\sin(\theta) = \frac{\text{opposite}}{\text{hypotenuse}}$",
        ]:
            self.assertEqual(sanitize_katex(text), text)

    def test_a_bare_token_in_plain_text_is_still_wrapped(self):
        self.assertEqual(sanitize_katex(r"the spread (\sigma) of $x(\alpha)$"),
                         r"the spread \(\sigma\) of $x(\alpha)$")


class SavingAHintTests(TestCase):

    def test_a_hint_with_brackets_in_its_maths_survives_save(self):
        hint = r"Law 9: $\left(\frac{a}{b}\right)^p$ and $\ln(\sqrt{x})$"
        q = Question.objects.create(topic=Topic.objects.create(name="Logs", slug="logs-t"),
                                    hint=hint)
        q.refresh_from_db()
        self.assertEqual(q.hint, hint)


class RepairTests(TestCase):

    def test_repair_unescapes_only_inside_dollar_maths(self):
        damaged = r"Use \(\sigma\) for spread. $\log_a\left\(\frac{x}{y}\right\)$ and $\ln\(x\)$"
        self.assertEqual(repair(damaged),
                         r"Use \(\sigma\) for spread. $\log_a\left(\frac{x}{y}\right)$ and $\ln(x)$")

    def test_the_command_fixes_damaged_hints_and_is_idempotent(self):
        topic = Topic.objects.create(name="Indices", slug="indices-t")
        q = Question.objects.create(topic=topic, hint="placeholder")
        # Written the way the old sanitizer left it, past save() on purpose.
        Question.objects.filter(pk=q.pk).update(hint=r"$\left\(\frac{a}{b}\right\)^p$")
        call_command("repair_hint_math_parens", stdout=open("/dev/null", "w"))
        q.refresh_from_db()
        self.assertEqual(q.hint, r"$\left(\frac{a}{b}\right)^p$")
        call_command("repair_hint_math_parens", stdout=open("/dev/null", "w"))
        q.refresh_from_db()
        self.assertEqual(q.hint, r"$\left(\frac{a}{b}\right)^p$")
