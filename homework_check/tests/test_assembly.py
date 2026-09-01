"""The rules that decide what gets printed on a student's sheet.

Every test here guards one thing: a report handed to a student must never
claim more than the model actually established. The two ways that goes wrong
are inventing an answer for a question the solutions PDF does not cover, and
putting a confident rating on photos that could not be read -- so those are
the cases tested hardest.

No database, no network, no API key: these are pure functions, and keeping
them that way is what makes this suite worth running on every change.
"""
from django.test import SimpleTestCase

from homework_check.services.assembly import (
    assemble, derive_rating, fallback_summary, merge_questions, tally,
)
from homework_check.services.check_analysis import _clean_questions


def q(label, verdict="correct", found=True, student="", correct="",
      comment="", continues=False):
    return {
        "label": label, "verdict": verdict, "found_in_solutions": found,
        "student_answer": student, "correct_answer": correct,
        "comment": comment, "continues": continues,
    }


def chunk(questions, readable=True, confidence="high", **extra):
    return {"questions": questions, "readable": readable,
            "confidence": confidence, **extra}


class CleanQuestionsTests(SimpleTestCase):
    """The model's rows are normalised before anything else sees them."""

    def test_drops_rows_without_a_label(self):
        self.assertEqual(_clean_questions([{"label": "  ", "verdict": "correct"}]), [])

    def test_unknown_verdict_becomes_unclear(self):
        row = _clean_questions([{"label": "1", "verdict": "brilliant"}])[0]
        self.assertEqual(row["verdict"], "unclear")

    def test_missing_keys_are_filled_not_raised(self):
        row = _clean_questions([{"label": "1"}])[0]
        self.assertEqual(row["student_answer"], "")
        self.assertEqual(row["correct_answer"], "")
        self.assertFalse(row["found_in_solutions"])

    def test_answer_is_stripped_when_question_was_not_in_the_solutions(self):
        """The invention the prompt forbids, refused a second time in code.

        If the model says it could not find the question but supplies an
        answer anyway, that answer is a guess, and printing it on a sheet
        handed to a student is the worst failure this tool has.
        """
        row = _clean_questions([{
            "label": "7", "found_in_solutions": False,
            "correct_answer": "x = 4", "verdict": "correct",
        }])[0]
        self.assertEqual(row["correct_answer"], "")
        self.assertEqual(row["verdict"], "unclear")

    def test_non_dict_rows_are_ignored(self):
        self.assertEqual(_clean_questions(["1(a)", None, 7]), [])


class MergeQuestionsTests(SimpleTestCase):
    """Working that ran across a page break arrives twice."""

    def test_same_label_in_two_chunks_becomes_one_row(self):
        merged = merge_questions([
            chunk([q("3", verdict="incomplete", comment="Started well.")]),
            chunk([q("3", verdict="slip", student="x = 4", comment="Sign error on line 3.")]),
        ])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["student_answer"], "x = 4")
        self.assertIn("Started well.", merged[0]["comment"])
        self.assertIn("Sign error", merged[0]["comment"])

    def test_worse_verdict_wins_on_merge(self):
        """An error seen on the second page is still an error."""
        merged = merge_questions([
            chunk([q("3", verdict="correct")]),
            chunk([q("3", verdict="wrong")]),
        ])
        self.assertEqual(merged[0]["verdict"], "wrong")

    def test_duplicate_comment_is_not_repeated(self):
        merged = merge_questions([
            chunk([q("3", comment="Check the discriminant.")]),
            chunk([q("3", comment="Check the discriminant.")]),
        ])
        self.assertEqual(merged[0]["comment"], "Check the discriminant.")

    def test_merged_row_is_no_longer_marked_as_continuing(self):
        merged = merge_questions([
            chunk([q("3", continues=True)]),
            chunk([q("3")]),
        ])
        self.assertFalse(merged[0]["continues"])

    def test_orders_the_way_a_copy_runs(self):
        merged = merge_questions([chunk([
            q("10"), q("2"), q("3(b)"), q("3(a)"),
        ])])
        self.assertEqual([r["label"] for r in merged],
                         ["2", "3(a)", "3(b)", "10"])


class DeriveRatingTests(SimpleTestCase):
    """A rating is the one thing on the sheet a student takes literally."""

    def test_all_correct_is_excellent(self):
        qs = [q(str(i)) for i in range(1, 6)]
        self.assertEqual(derive_rating(qs, [chunk(qs)])[0], "excellent")

    def test_a_slip_counts_for_half_not_nothing(self):
        """Sound method, arithmetic error. Not the same as not knowing how,
        so it must score better than a wrong method..."""
        slipped = [q("1"), q("2"), q("3", verdict="slip")]
        wronged = [q("1"), q("2"), q("3", verdict="wrong")]
        # 2.5/3 = 0.83 -> good, against 2/3 = 0.67 -> fair.
        self.assertEqual(derive_rating(slipped, [chunk(slipped)])[0], "good")
        self.assertEqual(derive_rating(wronged, [chunk(wronged)])[0], "fair")

    def test_slipping_every_question_is_not_excellent(self):
        """The reason a slip is not worth full credit.

        Counting slips as correct would hand a student who got every single
        answer wrong a sheet saying 'Excellent'.
        """
        qs = [q(str(i), verdict="slip") for i in range(1, 6)]
        self.assertEqual(derive_rating(qs, [chunk(qs)])[0], "fair")

    def test_incomplete_earns_nothing_but_is_still_judged(self):
        qs = [q("1"), q("2"), q("3", verdict="incomplete"), q("4")]
        self.assertEqual(derive_rating(qs, [chunk(qs)])[0], "good")

    def test_bands(self):
        for correct, total, expected in [(8, 10, "good"), (5, 10, "fair"), (3, 10, "poor")]:
            qs = ([q(str(i)) for i in range(correct)]
                  + [q(f"w{i}", verdict="wrong") for i in range(total - correct)])
            with self.subTest(band=expected):
                self.assertEqual(derive_rating(qs, [chunk(qs)])[0], expected)

    def test_withheld_when_a_photo_was_unreadable(self):
        qs = [q("1"), q("2"), q("3")]
        rating, reason = derive_rating(qs, [chunk(qs), chunk([], readable=False)])
        self.assertEqual(rating, "")
        self.assertIn("could not be read", reason)

    def test_withheld_on_low_confidence(self):
        qs = [q("1"), q("2"), q("3")]
        rating, reason = derive_rating(qs, [chunk(qs, confidence="low")])
        self.assertEqual(rating, "")
        self.assertIn("not confident", reason)

    def test_withheld_when_too_few_questions_were_matched(self):
        """One question is a photo problem, not a judgement on the student."""
        qs = [q("1"), q("2", verdict="unclear"), q("3", verdict="unclear")]
        rating, reason = derive_rating(qs, [chunk(qs)])
        self.assertEqual(rating, "")
        self.assertIn("too few questions", reason)

    def test_unclear_questions_are_excluded_not_counted_against(self):
        """A question missing from the PDF must not drag the rating down.

        The teacher may simply have scoped the page range too narrowly, which
        says nothing whatever about the student.
        """
        qs = [q("1"), q("2"), q("3"), q("4", verdict="unclear", found=False)]
        self.assertEqual(derive_rating(qs, [chunk(qs)])[0], "excellent")


class TallyTests(SimpleTestCase):
    def test_counts_every_verdict_and_the_gaps_in_the_solutions(self):
        counts = tally([
            q("1"), q("2", verdict="slip"), q("3", verdict="wrong"),
            q("4", verdict="unclear", found=False),
        ])
        self.assertEqual(counts["total"], 4)
        self.assertEqual(counts["correct"], 1)
        self.assertEqual(counts["slip"], 1)
        self.assertEqual(counts["wrong"], 1)
        self.assertEqual(counts["not_in_solutions"], 1)


class FallbackSummaryTests(SimpleTestCase):
    """Printed unreviewed when the summarising call fails, so it may only
    restate what the per-question rows already show."""

    def test_no_questions(self):
        self.assertIn("No questions", fallback_summary([], tally([])))

    def test_nothing_matched_to_the_solutions(self):
        qs = [q("1", verdict="unclear", found=False)]
        self.assertIn("none could be matched", fallback_summary(qs, tally(qs)))

    def test_names_the_slips_separately_from_the_wrong_methods(self):
        qs = [q("1"), q("2", verdict="slip"), q("3", verdict="wrong")]
        text = fallback_summary(qs, tally(qs))
        self.assertIn("1 of 3", text)
        self.assertIn("slip", text)
        self.assertIn("wrong approach", text)


class AssembleTests(SimpleTestCase):
    def test_takes_the_lowest_confidence_across_chunks(self):
        report = assemble([chunk([q("1")], confidence="high"),
                           chunk([q("2")], confidence="medium")])
        self.assertEqual(report["confidence"], "medium")

    def test_one_unreadable_chunk_makes_the_whole_report_unreadable(self):
        report = assemble([chunk([q("1")]), chunk([], readable=False)])
        self.assertFalse(report["readable"])

    def test_collects_teacher_notes_without_repeating_them(self):
        report = assemble([
            chunk([q("1")], notes="Photo 2 was cut off."),
            chunk([q("2")], notes="Photo 2 was cut off."),
            chunk([q("3")], notes="Q7 is not in the solutions."),
        ])
        self.assertEqual(report["notes"],
                         ["Photo 2 was cut off.", "Q7 is not in the solutions."])

    def test_diagram_feedback_only_from_chunks_that_saw_one(self):
        report = assemble([
            chunk([q("1")], has_diagram=False, diagram_feedback="ignored"),
            chunk([q("2")], has_diagram=True, diagram_feedback="No axis labels."),
        ])
        self.assertTrue(report["has_diagram"])
        self.assertEqual(report["diagram_feedback"], "No axis labels.")
