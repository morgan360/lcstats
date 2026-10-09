"""Answers with commas in them: lists, points and intervals.

Until October 2026 any answer containing "number, number" was marked as a
confidence interval -- in order, and on its first two numbers only. So a
reordered list of roots scored 20, the third value of a list was never
checked, and (5/6, 49/12) was read as (6, 49). These pin down each shape.
"""
from unittest import mock

from django.test import SimpleTestCase

from interactive_lessons import stats_tutor
from interactive_lessons.stats_tutor import mark_student_answer


def score(student, correct):
    # GPT is only asked for feedback or as a fallback; here it always says 0,
    # so a full score can only come from the local checks under test.
    with mock.patch.object(stats_tutor, "gpt_grade", return_value=(0, "gpt", "")):
        return mark_student_answer("Q", student, correct)["score"]


class BareListTests(SimpleTestCase):

    def test_a_list_of_roots_may_come_in_any_order(self):
        self.assertEqual(score("-13/5, 2", "2,-13/5"), 100)
        self.assertEqual(score("2, -2.6", "2,-13/5"), 100)

    def test_every_value_in_a_longer_list_is_checked(self):
        self.assertEqual(score("30, 60, 210, 240", "30,60,210,240"), 100)
        self.assertLess(score("30, 60, 210, 999", "30,60,210,240"), 100)
        self.assertEqual(score("240, 210, 60, 30", "30,60,210,240"), 100)

    def test_extra_values_are_not_a_full_match(self):
        self.assertLess(score("1, -2, 5", "1, -2"), 100)

    def test_a_single_value_is_unaffected(self):
        self.assertEqual(score("7", "7"), 100)
        self.assertLess(score("8", "7"), 100)


class OnePairTests(SimpleTestCase):

    def test_a_point_keeps_its_order(self):
        self.assertEqual(score("(2, 3)", "(2, 3)"), 100)
        self.assertLess(score("(3, 2)", "(2, 3)"), 100)

    def test_fractions_in_a_point_are_read_as_fractions(self):
        self.assertEqual(score("(0.833, 4.083)", "(5/6, 49/12)"), 100)
        self.assertEqual(score(r"\left(\frac{5}{6}, \frac{49}{12}\right)", "(5/6, 49/12)"), 100)

    def test_brackets_may_be_left_off_a_point(self):
        self.assertEqual(score("5/6, 49/12", "(5/6, 49/12)"), 100)

    def test_a_confidence_interval_still_works_every_way_it_is_written(self):
        for student in ["(0.810, 0.874)", "0.81, 0.874", "0.81 < p < 0.874", "[0.81, 0.874]"]:
            self.assertEqual(score(student, "(0.810, 0.874)"), 100, student)
        self.assertEqual(score("58.98 < μ < 63.03", "58.98 < μ < 63.03"), 100)

    def test_one_bound_right_is_partial_credit(self):
        self.assertEqual(score("(0.810, 0.900)", "(0.810, 0.874)"), 50)


class SeveralPointsTests(SimpleTestCase):

    def test_every_point_is_checked_in_any_order(self):
        correct = "(-6, 325), (1, -18)"
        self.assertEqual(score("(-6, 325), (1, -18)", correct), 100)
        self.assertEqual(score("(1, -18), (-6, 325)", correct), 100)
        self.assertLess(score("(-6, 325), (1, 18)", correct), 100)
        self.assertLess(score("(-6, 325)", correct), 100)

    def test_a_points_coordinates_keep_their_order(self):
        self.assertLess(score("(325, -6), (-18, 1)", "(-6, 325), (1, -18)"), 100)

    def test_labels_around_the_points_are_ignored(self):
        self.assertEqual(score("(-1/3, -22/27), (1, -2)",
                               "Maximum: (-1/3, -22/27), Minimum: (1, -2)"), 100)


class MixedAnswerTests(SimpleTestCase):

    def test_a_range_inside_a_longer_answer_does_not_earn_full_marks_alone(self):
        self.assertLess(score("[-1, 1]", "Period = 120°, Range: [-1, 1]"), 100)

    def test_an_answer_typed_exactly_as_stored_is_full_marks_without_gpt(self):
        correct = "x - 3y - 1 = 0, 3x - y - 3 = 0"
        self.assertEqual(score("x - 3y - 1 = 0, 3x - y - 3 = 0", correct), 100)
        self.assertEqual(score("x-3y-1=0,3x-y-3=0", correct), 100)

    def test_a_wrong_sign_no_longer_passes_on_a_stray_number_pair(self):
        # The old interval regex found "0, 3" in both and called it a match.
        self.assertLess(score("x - 3y - 1 = 0, 3x + y - 3 = 0",
                              "x - 3y - 1 = 0, 3x - y - 3 = 0"), 100)

    def test_a_sentence_answer_does_not_crash_the_grader(self):
        # compare_algebraic used to raise AttributeError on prose.
        self.assertEqual(score("It is going up so it is slowing down",
                               "Because it is going upwards. It is decelerating"), 0)
