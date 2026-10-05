"""A stored answer the numeric parser cannot read must go to GPT for a mark.

Practice part 262 stores "x=√2, y=2√2, z=√6", which parses to nothing, while a
student's "x=\\sqrt2;y=2\\sqrt2;z=\\sqrt6" parses to its first value. That
mismatch scored the correct answer a flat 50 without GPT ever marking it, and a
wrong x, which parsed to nothing, went to GPT and scored higher. The answers
below are the ones the student submitted on 2026-10-05.
"""
from unittest.mock import patch

from django.test import SimpleTestCase

from interactive_lessons.stats_tutor import mark_student_answer, normalise_numeric_answer

STORED = "x=√2, y=2√2, z=√6"


class UnparsedStoredAnswerTests(SimpleTestCase):

    def test_premise_stored_answer_does_not_parse(self):
        self.assertEqual(normalise_numeric_answer(STORED), [])
        self.assertTrue(normalise_numeric_answer(r"x=\sqrt2;y=2\sqrt2;z=\sqrt6"))

    @patch("interactive_lessons.stats_tutor.gpt_grade", return_value=(100, "Correct.", ""))
    def test_correct_answer_is_marked_by_gpt(self, gpt_grade):
        result = mark_student_answer("Find x, y and z.", r"x=\sqrt2;y=2\sqrt2;z=\sqrt6", STORED)
        gpt_grade.assert_called_once()
        self.assertEqual(result["score"], 100)

    @patch("interactive_lessons.stats_tutor.gpt_grade", return_value=(30, "z is wrong.", ""))
    def test_wrong_answer_takes_gpt_score_too(self, gpt_grade):
        result = mark_student_answer("Find x, y and z.", r"x=\sqrt2;y=2\sqrt2;z=2", STORED)
        self.assertEqual(result["score"], 30)

    @patch("interactive_lessons.stats_tutor.gpt_grade", return_value=(90, "", ""))
    def test_parsed_wrong_numeric_answer_still_scores_50(self, gpt_grade):
        result = mark_student_answer("Find x.", "7", "5")
        self.assertEqual(result["score"], 50)
