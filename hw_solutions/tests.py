"""Finding the exercises inside a solutions PDF.

The detector reads a running header, so the cases that matter are a PDF that
has one, a PDF that does not, and the cross-reference in body text that must
not be mistaken for an exercise starting.
"""
import os
import tempfile

from django.test import SimpleTestCase

from hw_solutions.services import detect_sections


def make_pdf(pages):
    """A PDF whose pages carry the given header lines."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    path = tempfile.mktemp(suffix='.pdf')
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    for lines in pages:
        c.setFont("Helvetica", 12)
        y = h - 50
        for line in lines:
            c.drawString(50, y, line)
            y -= 18
        c.showPage()
    c.save()
    return path


class DetectSectionsTests(SimpleTestCase):

    def tearDown(self):
        for p in getattr(self, '_paths', []):
            os.unlink(p)

    def pdf(self, pages):
        path = make_pdf(pages)
        self._paths = getattr(self, '_paths', []) + [path]
        return path

    def test_finds_contiguous_runs_and_their_page_ranges(self):
        path = self.pdf([
            ["Chapter 1 Algebra"],          # p1, no exercise
            ["Exercise 1.1", "Q1 ..."],     # p2
            ["Exercise 1.1", "Q7 ..."],     # p3
            ["Exercise 1.2", "Q1 ..."],     # p4
            ["Exercise 1.2", "Q5 ..."],     # p5
            ["Exercise 1.2", "Q9 ..."],     # p6
        ])
        self.assertEqual(detect_sections(path), [
            {"label": "Exercise 1.1", "first_page": 2, "last_page": 3},
            {"label": "Exercise 1.2", "first_page": 4, "last_page": 6},
        ])

    def test_a_pdf_with_no_headings_yields_nothing(self):
        """The signal to fall back to a hand-typed page range."""
        path = self.pdf([["Just some worked solutions"], ["More of them"]])
        self.assertEqual(detect_sections(path), [])

    def test_the_running_header_wins_over_a_mention_further_down(self):
        """'see Exercise 1.9' in the body must not start a new section."""
        path = self.pdf([
            ["Exercise 1.1", "Q1 ...", "compare with Exercise 1.9 later"],
            ["Exercise 1.1", "Q4 ..."],
        ])
        self.assertEqual(detect_sections(path), [
            {"label": "Exercise 1.1", "first_page": 1, "last_page": 2},
        ])

    def test_a_single_page_exercise_is_kept(self):
        path = self.pdf([["Exercise 2.1", "Q1"], ["Exercise 2.2", "Q1"]])
        labels = [s["label"] for s in detect_sections(path)]
        self.assertEqual(labels, ["Exercise 2.1", "Exercise 2.2"])

    def test_a_whole_number_exercise_is_matched(self):
        path = self.pdf([["Exercise 7", "Q1"]])
        self.assertEqual(detect_sections(path)[0]["label"], "Exercise 7")

    def test_case_is_ignored_but_the_label_reads_normally(self):
        path = self.pdf([["EXERCISE 3.2", "Q1"]])
        self.assertEqual(detect_sections(path)[0]["label"], "Exercise 3.2")

    def test_an_exercise_that_resumes_later_is_reported_as_two_runs(self):
        """Honest about what is on the page rather than merging across a gap."""
        path = self.pdf([
            ["Exercise 1.1"], ["Revision notes"], ["Exercise 1.1"],
        ])
        found = detect_sections(path)
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["first_page"], 1)
        self.assertEqual(found[1]["first_page"], 3)


class RunningHeaderTests(SimpleTestCase):
    """The cases a real chapter of Active Maths 4 threw up, which the
    hand-written fixtures above all missed.

    Its running header is four lines -- book, page number, section, chapter
    number -- so the section heading sits on a line of its own with the
    chapter number printed directly beneath it.
    """

    def tearDown(self):
        for p in getattr(self, '_paths', []):
            os.unlink(p)

    def pdf(self, pages):
        path = make_pdf(pages)
        self._paths = getattr(self, '_paths', []) + [path]
        return path

    def test_the_chapter_number_beneath_a_named_header_is_not_an_exercise(self):
        """'Revision Exercise' over '07' was being read as 'Exercise 07'."""
        path = self.pdf([
            ["ACTIVE MATHS 4 BOOK 1", "53", "Revision Exercise", "07",
             "Indices and Logarithms"],
        ])
        labels = [s["label"] for s in detect_sections(path)]
        self.assertNotIn("Exercise 07", labels)
        self.assertEqual(labels, ["Revision Exercise"])

    def test_named_sections_at_the_back_of_a_chapter_are_pickable(self):
        """These are set for homework as often as the numbered exercises."""
        path = self.pdf([
            ["ACTIVE MATHS 4 BOOK 1", "1", "Exercise 7.1", "07"],
            ["ACTIVE MATHS 4 BOOK 1", "2", "Revision Exercise", "07"],
            ["ACTIVE MATHS 4 BOOK 1", "3", "Revision Exercise", "07"],
            ["ACTIVE MATHS 4 BOOK 1", "4", "Exam Questions", "07"],
        ])
        self.assertEqual(detect_sections(path), [
            {"label": "Exercise 7.1", "first_page": 1, "last_page": 1},
            {"label": "Revision Exercise", "first_page": 2, "last_page": 3},
            {"label": "Exam Questions", "first_page": 4, "last_page": 4},
        ])

    def test_a_hyphenated_named_section_is_matched(self):
        path = self.pdf([["Exam-style Questions", "07"]])
        self.assertEqual(detect_sections(path)[0]["label"], "Exam-style Questions")

    def test_a_sentence_ending_in_questions_is_not_a_heading(self):
        """Long enough to be prose, so the length guard rejects it."""
        path = self.pdf([
            ["Use the laws of indices to answer each of the following questions"],
        ])
        self.assertEqual(detect_sections(path), [])

    def test_a_heading_mid_line_does_not_count(self):
        """Only a line that *is* the heading, not one that mentions it."""
        path = self.pdf([["See Exercise 7.9 for a worked example"]])
        self.assertEqual(detect_sections(path), [])


class BuildSectionsDedupTests(SimpleTestCase):
    """detect_sections reports what is on the page; build_sections has to
    survive storing it under a (solution, label) uniqueness constraint."""

    def test_the_longest_run_wins_when_a_label_repeats(self):
        from hw_solutions.services import _longest_run_per_label
        kept = _longest_run_per_label([
            {"label": "Exercise 1.1", "first_page": 2, "last_page": 8},
            {"label": "Exercise 1.2", "first_page": 9, "last_page": 12},
            {"label": "Exercise 1.1", "first_page": 40, "last_page": 40},
        ])
        self.assertEqual(len(kept), 2)
        by_label = {s["label"]: s for s in kept}
        self.assertEqual(by_label["Exercise 1.1"]["first_page"], 2)
        self.assertEqual(by_label["Exercise 1.1"]["last_page"], 8)

    def test_result_is_in_page_order(self):
        from hw_solutions.services import _longest_run_per_label
        kept = _longest_run_per_label([
            {"label": "Exercise 1.3", "first_page": 20, "last_page": 25},
            {"label": "Exercise 1.1", "first_page": 2, "last_page": 8},
        ])
        self.assertEqual([s["label"] for s in kept],
                         ["Exercise 1.1", "Exercise 1.3"])

    def test_labels_are_unique_so_the_constraint_cannot_be_violated(self):
        from hw_solutions.services import _longest_run_per_label
        kept = _longest_run_per_label([
            {"label": "Exercise 1.1", "first_page": i, "last_page": i}
            for i in range(1, 6)
        ])
        self.assertEqual(len(kept), 1)
