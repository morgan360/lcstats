"""LaTeX answers from MathLive are marked by the local checks, not sent to GPT.

The answer box sends LaTeX (getValue("latex")). SymPy's LaTeX parser needs antlr4,
which is installed nowhere we run, so \\frac and \\sqrt used to fail both local
checks: 172 of 2,261 real answers on production went to GPT only for that. Every
input below is a form a student actually submitted.
"""
from django.test import SimpleTestCase

from interactive_lessons.services.utils_math import compare_algebraic, latex_to_plain
from interactive_lessons.stats_tutor import (
    compare_answers, compare_ignoring_one_sided_degrees, normalise_numeric_answer,
)


def numeric_match(student, correct):
    return compare_answers(normalise_numeric_answer(student),
                           normalise_numeric_answer(correct)) == 1.0


class LatexToPlainTests(SimpleTestCase):

    def test_fractions_with_and_without_braces(self):
        self.assertEqual(latex_to_plain(r"\frac{2}{15}"), "((2)/(15))")
        self.assertEqual(latex_to_plain(r"\frac13"), "((1)/(3))")
        self.assertEqual(latex_to_plain(r"\dfrac{5}{41}"), "((5)/(41))")

    def test_nested_and_sized_brackets(self):
        self.assertEqual(latex_to_plain(r"\frac{\left(12+44i\right)}{10}"), "(((12+44i))/(10))")
        self.assertEqual(latex_to_plain(r"\frac{\delta}{\sqrt{n}}"), r"((\delta)/((sqrt(n))))")

    def test_roots(self):
        self.assertEqual(latex_to_plain(r"3\cdot\sqrt2"), "3*(sqrt(2))")
        self.assertEqual(latex_to_plain(r"\sqrt[3]{8}"), "((8)**(1/(3)))")

    def test_named_constants_cannot_fuse_with_a_following_letter(self):
        self.assertEqual(latex_to_plain(r"2\pi r"), "2(pi) r")
        self.assertEqual(latex_to_plain(r"1.2+4.4\imaginaryI"), "1.2+4.4(i)")

    def test_degrees(self):
        self.assertEqual(latex_to_plain(r"45^{\circ}"), "45°")

    def test_plain_text_is_untouched(self):
        for text in ("2/15", "x^2+1", "Mean 23, Mode 24", ""):
            self.assertEqual(latex_to_plain(text), text)


class LatexAnswersAreMarkedLocallyTests(SimpleTestCase):

    def test_fraction_against_plain_answer(self):
        self.assertTrue(numeric_match(r"\frac{2}{15}", "2/15"))
        self.assertTrue(numeric_match(r"\frac12", "1/2"))        # GPT had scored this 0

    def test_plain_answer_against_latex_stored_answer(self):
        self.assertTrue(numeric_match("3/4", r"$\frac{3}{4}$"))   # GPT had scored this 50
        self.assertTrue(numeric_match("-4/3", r"$-\frac{4}{3}$"))

    def test_algebraic_forms(self):
        self.assertTrue(compare_algebraic(r"2\sqrt{3}", "2*sqrt(3)"))
        self.assertTrue(compare_algebraic(
            r"\frac{5x}{\left(3x-2\right)\left(2x-3\right)}", "5x/((2x-3)(3x-2))"))
        self.assertTrue(compare_algebraic(r"\frac{1}{py^2}", "1/(p*y^2)"))
        self.assertTrue(compare_algebraic("1.2+4.4\\imaginaryI", r"$\dfrac{12 + 44i}{10}$"))

    def test_wrong_answers_still_fail(self):
        self.assertFalse(compare_algebraic(r"\frac{1}{2}", "1/3"))
        self.assertFalse(compare_algebraic(r"\frac{x+1}{x+2}", "(x+1)/(x-2)"))
        self.assertFalse(numeric_match(r"\frac{x+1}{x+2}", "(x+1)/(x-2)"))


class ToleranceTests(SimpleTestCase):

    def test_rounded_to_two_places_is_accepted(self):
        self.assertTrue(numeric_match("0.13", "2/15"))
        self.assertTrue(numeric_match("904.78", "288*pi"))

    def test_close_but_wrong_small_answer_is_not(self):
        # 12/52 = 0.231 sat inside the old flat +-0.02 of 1/4.
        self.assertFalse(numeric_match(r"\frac{12}{52}", "1/4"))

    def test_tiny_probabilities_need_their_significant_figures(self):
        self.assertTrue(numeric_match("0.00000369", r"$\frac{1}{270725}$"))
        self.assertFalse(numeric_match("0.001", r"$\frac{1}{270725}$"))

    def test_large_answers_keep_the_old_tolerance(self):
        self.assertTrue(numeric_match("1080.01", "1080"))


class OneSidedDegreeSignTests(SimpleTestCase):
    """° reads as *pi/180, so 53 and a stored 53° used to differ by 57 times."""

    def test_bare_number_against_stored_degrees(self):
        self.assertEqual(compare_ignoring_one_sided_degrees("53", "53°"), 1.0)
        self.assertEqual(compare_ignoring_one_sided_degrees("30", r"$30^\circ$"), 1.0)

    def test_degree_sign_against_stored_bare_number(self):
        self.assertEqual(compare_ignoring_one_sided_degrees("40°", "40"), 1.0)
        self.assertEqual(compare_ignoring_one_sided_degrees(r"40^{\circ}", "40"), 1.0)

    def test_wrong_angle_still_fails(self):
        self.assertEqual(compare_ignoring_one_sided_degrees("50", "40°"), 0.0)

    def test_does_not_apply_when_both_sides_agree(self):
        self.assertIsNone(compare_ignoring_one_sided_degrees("40°", "40°"))
        self.assertIsNone(compare_ignoring_one_sided_degrees("40", "40"))

    def test_radians_are_not_mistaken_for_degrees(self):
        # 30 is not pi/6: only the degree sign is dropped, never a unit invented.
        self.assertEqual(compare_ignoring_one_sided_degrees("30°", "pi/6"), 0.0)
        self.assertTrue(numeric_match("30°", "pi/6"))
