"""A part's marking scheme is one image.

letter_region decides what that image covers when cut from the scheme;
flatten_solution_images folds the crops stacked by the old sub-part merge.
"""
import tempfile
from io import BytesIO, StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image

from core.models import Subject
from exam_papers.models import (
    ExamPaper, ExamPartSolutionImage, ExamQuestion, ExamQuestionPart,
)
from exam_papers.utils import letter_region
from interactive_lessons.models import Topic


class LetterRegionTests(SimpleTestCase):
    def test_every_row_for_the_letter_is_covered(self):
        """The shape of 2025 P2 Q9(a): a "(a)(i)(ii)" row read as the whole
        letter, which used to hide the (ii) and (iv) rows behind it."""
        regions = {
            (9, 'a', None): {'slices': [(64, 62, 802), (65, 62, 256)], 'width': 595},
            (9, 'a', 'ii'): {'slices': [(64, 400, 802)], 'width': 595},
            (9, 'a', 'iv'): {'slices': [(65, 200, 700)], 'width': 595},
            (9, 'b', None): {'slices': [(65, 700, 802)], 'width': 595},
        }
        self.assertEqual(letter_region(regions, 9, 'a')['slices'],
                         [(64, 62, 802), (65, 62, 700)])

    def test_a_repeated_slice_is_cut_once(self):
        """2022 P2 Q8(a) listed the same strip of page 21 twice."""
        regions = {
            (8, 'a', None): {'slices': [(20, 72, 357), (21, 69, 106)], 'width': 595},
            (8, 'a', 'ii'): {'slices': [(20, 349, 802), (21, 69, 106)], 'width': 595},
        }
        self.assertEqual(letter_region(regions, 8, 'a')['slices'],
                         [(20, 72, 802), (21, 69, 106)])

    def test_rows_that_do_not_touch_stay_separate(self):
        """The gap between them is a table header, not part of the solution."""
        regions = {
            (5, 'a', 'i'): {'slices': [(10, 100, 200)], 'width': 595},
            (5, 'a', 'ii'): {'slices': [(10, 250, 300)], 'width': 600},
        }
        region = letter_region(regions, 5, 'a')
        self.assertEqual(region['slices'], [(10, 100, 200), (10, 250, 300)])
        self.assertEqual(region['width'], 600)

    def test_no_region_for_the_letter(self):
        self.assertIsNone(letter_region({}, 5, 'a'))
        self.assertIsNone(letter_region(None, 5, 'a'))


def png(height, shade=0):
    buffer = BytesIO()
    Image.new('RGB', (4, height), (shade, shade, shade)).save(buffer, 'PNG')
    return SimpleUploadedFile(f'crop{height}_{shade}.png', buffer.getvalue(),
                              content_type='image/png')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='flatten-crops-test-'))
class FlattenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maths = Subject.objects.get(slug='maths')
        topic = Topic.objects.create(name='Probability', subject=maths, paper='p2')
        paper = ExamPaper.objects.create(subject=maths, year=2025, paper_type='p2',
                                         total_marks=300, is_published=True)
        cls.question = ExamQuestion.objects.create(
            exam_paper=paper, question_number=9, topic=topic, total_marks=50)

    def stacked(self, label, *crops):
        part = ExamQuestionPart.objects.create(
            question=self.question, label=label, max_marks=10,
            solution_image=crops[0])
        for index, crop in enumerate(crops[1:]):
            ExamPartSolutionImage.objects.create(part=part, order=index, image=crop)
        return part

    def flatten(self, *extra):
        out = StringIO()
        call_command('flatten_solution_images', *extra, stdout=out)
        return out.getvalue()

    def height(self, part):
        part.refresh_from_db()
        part.solution_image.open('rb')
        try:
            return Image.open(part.solution_image).height
        finally:
            part.solution_image.close()

    def test_report_only_changes_nothing(self):
        part = self.stacked('(a)', png(3), png(5, shade=200))
        output = self.flatten()
        self.assertIn('2 crops stitched', output)
        self.assertEqual(part.extra_solution_images.count(), 1)

    def test_apply_joins_the_stack_into_one_image(self):
        part = self.stacked('(a)', png(3), png(5, shade=200), png(3))
        output = self.flatten('--apply')
        self.assertIn('1 repeat dropped', output)
        self.assertEqual(self.height(part), 8)
        self.assertFalse(ExamPartSolutionImage.objects.exists())
        self.assertEqual(len(part.solution_images), 1)

    def test_a_part_with_one_crop_is_left_alone(self):
        part = ExamQuestionPart.objects.create(
            question=self.question, label='(b)', max_marks=10,
            solution_image=png(3))
        name = part.solution_image.name
        self.flatten('--apply')
        part.refresh_from_db()
        self.assertEqual(part.solution_image.name, name)

    def test_recut_without_a_scheme_falls_back_to_stitching(self):
        part = self.stacked('(a)', png(3), png(5, shade=200))
        output = self.flatten('--recut', '--apply')
        self.assertIn('no region in the scheme', output)
        self.assertEqual(self.height(part), 8)
