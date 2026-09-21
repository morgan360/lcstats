"""Reading part marks off a marking scheme.

Two failures these cover, both of which were silent in production:

* A scheme that heads a question with a bare "10" instead of "Q10" left that
  question with no region at all, and let the previous question's region run
  on through its pages - so Q9 came out worth double and Q10 nothing.
* A part covering sub-parts carries one "Scale" line per sub-part, and reading
  only the first understates its maximum, which inflates every score against it.
"""
import os
import tempfile
from io import StringIO

import fitz
from django.core.management import call_command
from django.test import TestCase, override_settings

from core.models import Subject
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart
from exam_papers.utils import (
    detect_marking_scheme_layout, regions_for_letter, scale_marks_for_region,
)

# Column positions copied from a real scheme: labels at x=63, the model
# solution at x=98, the marking notes at x=317. _LABEL_COLUMN_X is 110, so
# only the first counts as a label.
LABEL_X, SOLUTION_X, NOTES_X = 63, 98, 317

# detect_marking_scheme_layout trims trailing pages carrying under 250
# characters, on the grounds that they are cover sheets or blanks. Real pages
# are dense with marking notes, so test pages have to be too or the last one
# silently disappears.
NOTES = [
    'Low Partial Credit:',
    'Work of merit, for example, correct substitution of the given value',
    'Mid Partial Credit:',
    'One part correct, or work of merit in both of the parts above',
    'High Partial Credit:',
    'One part correct and work of merit in the other part of the question',
    'Full Credit -1:',
    'Apply a * for incorrect rounding, or for an answer given with no units',
]


def build_scheme(path, pages):
    """Write a marking-scheme PDF. Each page is a list of (x, y, text)."""
    doc = fitz.open()
    for rows in pages:
        page = doc.new_page(width=595, height=842)
        for x, y, text in rows:
            page.insert_text((x, y), text, fontsize=9)
        # Pad past the 250-character trim threshold.
        for offset, line in enumerate(NOTES):
            page.insert_text((NOTES_X, 640 + offset * 12), line, fontsize=8)
    doc.save(path)
    doc.close()


def question_row(y, heading):
    """The header row of a question's table: heading, then the two cells."""
    return [(LABEL_X, y, heading),
            (SOLUTION_X, y, 'Model Solution - 50 Marks'),
            (NOTES_X, y, 'Marking Notes')]


def part_row(y, label, scale):
    return [(LABEL_X, y, label),
            (SOLUTION_X, y, 'some working'),
            (NOTES_X, y, f'Scale {scale}C (0, 3, 7, {scale})')]


def sub_rows(y, letter, roman, scale):
    """A sub-part row: the letter and its numeral stacked in the label column."""
    return [(LABEL_X, y, f'({letter})'), (LABEL_X, y + 15, f'({roman})'),
            (NOTES_X, y, f'Scale {scale}B (0, 2, {scale})')]


class BareQuestionHeadingTests(TestCase):
    """A question headed "10" rather than "Q10" is still a question."""

    def scheme(self, pages):
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        build_scheme(tmp.name, pages)
        return tmp.name

    def test_bare_number_beside_model_solution_starts_a_question(self):
        path = self.scheme([
            question_row(63, 'Q9') + part_row(120, '(a)', 10),
            # The real 2025 deferred scheme drops the Q here.
            question_row(63, '10') + part_row(120, '(a)', 15),
        ])
        regions = detect_marking_scheme_layout(path, 1)
        self.assertIn((9, 'a', None), regions)
        self.assertIn((10, 'a', None), regions)

    def test_q9_no_longer_runs_on_into_q10s_page(self):
        path = self.scheme([
            question_row(63, 'Q9') + part_row(120, '(a)', 10),
            question_row(63, '10') + part_row(120, '(a)', 15),
        ])
        regions = detect_marking_scheme_layout(path, 1)
        pages = {page for region in regions_for_letter(regions, 9, 'a')
                 for page, _, _ in region['slices']}
        self.assertEqual(pages, {0}, "Q9(a) should not reach Q10's page")

    def test_marks_no_longer_double_up_on_the_previous_question(self):
        path = self.scheme([
            question_row(63, 'Q9') + part_row(120, '(a)', 10),
            question_row(63, '10') + part_row(120, '(a)', 15),
        ])
        regions = detect_marking_scheme_layout(path, 1)
        q9 = sum(scale_marks_for_region(path, r) or 0
                 for r in regions_for_letter(regions, 9, 'a'))
        q10 = sum(scale_marks_for_region(path, r) or 0
                  for r in regions_for_letter(regions, 10, 'a'))
        self.assertEqual((q9, q10), (10, 15))

    def test_a_bare_number_alone_in_the_column_is_not_a_heading(self):
        """Q10's page carries a table of t-values down the label column."""
        path = self.scheme([
            question_row(63, 'Q1')
            + part_row(120, '(a)', 10)
            # A table of values, sitting exactly where a heading would.
            + [(LABEL_X, 200, '0'), (LABEL_X, 220, '4'), (LABEL_X, 240, '8'),
               (LABEL_X, 260, '12'), (LABEL_X, 280, '16')],
        ])
        regions = detect_marking_scheme_layout(path, 1)
        found = sorted({key[0] for key in regions})
        self.assertEqual(found, [1], f'stray values started questions: {found}')


class ScaleMarksTests(TestCase):
    def scheme(self, pages):
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        build_scheme(tmp.name, pages)
        return tmp.name

    def test_sums_every_scale_in_the_region(self):
        """A part covering (i) and (ii) is worth both scales, not the first."""
        path = self.scheme([
            question_row(63, 'Q6') + part_row(120, '(a)', 20)
            + sub_rows(300, 'b', 'i', 5) + sub_rows(400, 'b', 'ii', 5),
        ])
        regions = detect_marking_scheme_layout(path, 1)
        total = sum(scale_marks_for_region(path, region) or 0
                    for region in regions_for_letter(regions, 6, 'b'))
        self.assertEqual(total, 10, "both of (b)'s scales should count")

    def test_region_without_a_scale_reads_as_none(self):
        """Where two letters share one scale, the second has none of its own."""
        path = self.scheme([
            question_row(63, 'Q7')
            + [(LABEL_X, 120, '(a)'), (SOLUTION_X, 120, 'working only')]
            + part_row(300, '(b)', 10),
        ])
        regions = detect_marking_scheme_layout(path, 1)
        regs = regions_for_letter(regions, 7, 'a')
        self.assertTrue(regs)
        self.assertIsNone(scale_marks_for_region(path, regs[0]))


MEDIA = tempfile.mkdtemp(prefix='marking-info-test-')


@override_settings(MEDIA_ROOT=MEDIA)
class VerifyTotalTests(TestCase):
    """The total check is on unless it is explicitly turned off."""

    def setUp(self):
        maths = Subject.objects.get(slug='maths')
        self.paper = ExamPaper.objects.create(
            subject=maths, year=2031, paper_type='p1', total_marks=300)
        self.question = ExamQuestion.objects.create(
            exam_paper=self.paper, question_number=6, title='Q6',
            total_marks=30, order=6)
        for order, label in enumerate(['(a)', '(b)'], start=1):
            ExamQuestionPart.objects.create(
                question=self.question, label=label, order=order, max_marks=0)

        # (a) is worth 20 and (b) two scales of 5 - together the stated 30.
        build_scheme(os.path.join(MEDIA, 'scheme.pdf'), [
            question_row(63, 'Q6') + part_row(120, '(a)', 20)
            + sub_rows(300, 'b', 'i', 5) + sub_rows(400, 'b', 'ii', 5),
        ])
        self.paper.marking_scheme_pdf.name = 'scheme.pdf'
        self.paper.save(update_fields=['marking_scheme_pdf'])

    def run_command(self, *args):
        out = StringIO()
        call_command('auto_extract_marking_info', self.paper.id,
                     *args, stdout=out, stderr=out)
        return out.getvalue()

    def marks(self):
        return {p.label: p.max_marks
                for p in self.question.parts.all().order_by('order')}

    def test_reads_from_the_scheme_text_without_vision(self):
        output = self.run_command('--no-vision')
        self.assertIn('scheme text', output)
        self.assertEqual(self.marks(), {'(a)': 20, '(b)': 10})

    def test_dry_run_saves_nothing(self):
        self.run_command('--no-vision', '--dry-run')
        self.assertEqual(self.marks(), {'(a)': 0, '(b)': 0})

    def test_mismatched_total_is_refused_by_default(self):
        """Say the paper thinks the question is worth 40; 30 must not be saved."""
        self.question.total_marks = 40
        self.question.save(update_fields=['total_marks'])
        output = self.run_command('--no-vision')
        self.assertIn('needs entering by hand', output)
        self.assertEqual(self.marks(), {'(a)': 0, '(b)': 0})

    def test_no_verify_total_writes_anyway(self):
        self.question.total_marks = 40
        self.question.save(update_fields=['total_marks'])
        output = self.run_command('--no-vision', '--no-verify-total')
        self.assertIn('Total check disabled', output)
        self.assertEqual(self.marks(), {'(a)': 20, '(b)': 10})
