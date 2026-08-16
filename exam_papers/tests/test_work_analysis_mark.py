"""The estimated mark, and every case where it must be withheld.

"No marks, ever" was the v1 decision, the failure mode being an OCR misread
becoming a mark a student believes. The mark is now given for exam parts, so
the guards that make that safe are the thing worth testing: the prompt asks for
them, but a prompt is not a guarantee, and _sanitise_mark decides in code.
"""
from django.test import SimpleTestCase

from exam_papers.services.work_analysis import _build_prompt, _sanitise_mark


def result(**overrides):
    base = {"readable": True, "has_working": True, "confidence": "high",
            "estimated_mark": 7, "mark_reasoning": "Method sound throughout."}
    base.update(overrides)
    return base


class SanitiseMarkTests(SimpleTestCase):
    def test_a_good_mark_survives(self):
        r = result()
        _sanitise_mark(r, 10)
        self.assertEqual(r["estimated_mark"], 7)
        self.assertEqual(r["estimated_max_marks"], 10)

    def test_no_max_marks_means_no_mark(self):
        r = result()
        _sanitise_mark(r, None)
        self.assertIsNone(r["estimated_mark"])
        self.assertIsNone(r["estimated_max_marks"])
        self.assertEqual(r["mark_reasoning"], "")

    def test_unreadable_page_is_not_marked(self):
        r = result(readable=False)
        _sanitise_mark(r, 10)
        self.assertIsNone(r["estimated_mark"])

    def test_low_confidence_is_not_marked(self):
        r = result(confidence="low")
        _sanitise_mark(r, 10)
        self.assertIsNone(r["estimated_mark"])

    def test_blank_page_is_not_marked(self):
        r = result(has_working=False)
        _sanitise_mark(r, 10)
        self.assertIsNone(r["estimated_mark"])

    def test_mark_above_the_maximum_is_discarded(self):
        r = result(estimated_mark=12)
        _sanitise_mark(r, 10)
        self.assertIsNone(r["estimated_mark"])

    def test_negative_mark_is_discarded(self):
        r = result(estimated_mark=-1)
        _sanitise_mark(r, 10)
        self.assertIsNone(r["estimated_mark"])

    def test_zero_is_a_real_mark_not_a_missing_one(self):
        r = result(estimated_mark=0)
        _sanitise_mark(r, 10)
        self.assertEqual(r["estimated_mark"], 0)

    def test_numeric_string_is_accepted(self):
        r = result(estimated_mark="7")
        _sanitise_mark(r, 10)
        self.assertEqual(r["estimated_mark"], 7)

    def test_float_is_rounded_to_a_whole_mark(self):
        r = result(estimated_mark=6.5)
        _sanitise_mark(r, 10)
        self.assertEqual(r["estimated_mark"], 6)

    def test_prose_instead_of_a_number_is_discarded(self):
        r = result(estimated_mark="about 7 out of 10")
        _sanitise_mark(r, 10)
        self.assertIsNone(r["estimated_mark"])

    def test_true_is_not_a_mark(self):
        """bool is an int subclass, so True would otherwise sanitise to 1."""
        r = result(estimated_mark=True)
        _sanitise_mark(r, 10)
        self.assertIsNone(r["estimated_mark"])

    def test_missing_key_is_tolerated(self):
        r = result()
        del r["estimated_mark"]
        _sanitise_mark(r, 10)
        self.assertIsNone(r["estimated_mark"])


class PromptTests(SimpleTestCase):
    def test_marking_is_requested_when_scheme_and_marks_are_present(self):
        p = _build_prompt("Solve for x.", "(a)", None, has_scheme=True, max_marks=10)
        self.assertIn("estimated_mark", p)
        self.assertIn("out of 10", p)
        self.assertNotIn("Do not award marks or a score", p)

    def test_marking_is_forbidden_without_max_marks(self):
        p = _build_prompt("Solve for x.", "(a)", None, has_scheme=True, max_marks=None)
        self.assertNotIn("estimated_mark", p)
        self.assertIn("do NOT award a mark or a score", p)
        self.assertIn("Do not award marks or a score", p)

    def test_practice_questions_are_never_marked(self):
        """No scheme, no marks - the interactive-lessons path."""
        p = _build_prompt("Solve for x.", "(a)", "x = 3", has_scheme=False, max_marks=None)
        self.assertNotIn("estimated_mark", p)
        self.assertIn("Do not award marks or a score", p)

    def test_answer_leak_rule_survives_in_the_marking_prompt(self):
        p = _build_prompt("Solve for x.", "(a)", "x = 3", has_scheme=True, max_marks=10)
        self.assertIn("Never give the answer away", p)
        self.assertIn("must not hand over the missing work", p)
