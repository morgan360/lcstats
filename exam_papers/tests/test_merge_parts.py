"""Folding sub-parts into one part per letter.

The command deletes rows, and every foreign key pointing at a part cascades,
so most of what is tested here is that nothing a student did goes with them.
"""
import tempfile
from io import StringIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from core.models import Subject
from exam_papers.models import (
    ExamAttempt, ExamPaper, ExamPartSolutionImage, ExamQuestion,
    ExamQuestionAttempt, ExamQuestionPart,
)
from interactive_lessons.models import Topic


PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
       b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00'
       b'\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')


def image(name):
    return SimpleUploadedFile(name, PNG, content_type='image/png')


# Saving an ImageField in a test writes a real file, and the test runner does
# not isolate MEDIA_ROOT -- so without this the crop tests below quietly litter
# the project's own media/exam_papers/marking_schemes with 1x1 PNGs.
@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='merge-parts-test-'))
class MergeTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(name='Integration', subject=cls.maths,
                                         paper='p1')
        cls.paper = ExamPaper.objects.create(
            subject=cls.maths, year=2019, paper_type='p1',
            total_marks=300, is_published=True,
        )
        cls.question = ExamQuestion.objects.create(
            exam_paper=cls.paper, question_number=6, topic=cls.topic,
            total_marks=30,
        )
        cls.student = User.objects.create_user('student', password='pw')

    def part(self, label, **kwargs):
        kwargs.setdefault('max_marks', 10)
        kwargs.setdefault('order', 0)
        return ExamQuestionPart.objects.create(
            question=self.question, label=label, **kwargs)

    def merge(self, *extra):
        out = StringIO()
        call_command('merge_question_parts', *extra, stdout=out, stderr=out)
        return out.getvalue()

    def labels(self):
        return list(ExamQuestionPart.objects
                    .filter(question=self.question)
                    .order_by('order', 'id').values_list('label', flat=True))


class LabelTests(MergeTestBase):
    def test_a_canonical_part_is_left_alone(self):
        part = self.part('(a)')
        self.merge('--apply')

        part.refresh_from_db()
        self.assertEqual(part.label, '(a)')
        self.assertEqual(self.labels(), ['(a)'])

    def test_a_messy_label_is_tidied_without_deleting_anything(self):
        part = self.part('b(ii)')
        self.merge('--apply')

        part.refresh_from_db()
        self.assertEqual(part.label, '(b)')
        self.assertEqual(ExamQuestionPart.objects.count(), 1)

    def test_a_label_whose_letter_is_inside_a_word_is_skipped(self):
        """parse_part_label reads "Part (b)" as letter a, the a of Part."""
        part = self.part('Part (b)')
        output = self.merge('--apply')

        part.refresh_from_db()
        self.assertEqual(part.label, 'Part (b)')
        self.assertIn('label unreadable', output)


class MergeTests(MergeTestBase):
    def test_two_sub_parts_become_one_and_the_first_survives(self):
        first = self.part('(c) (i)', max_marks=5, order=3)
        second = self.part('(c) (ii)', max_marks=10, order=4)
        self.merge('--apply')

        self.assertEqual(self.labels(), ['(c)'])
        survivor = ExamQuestionPart.objects.get()
        self.assertEqual(survivor.pk, first.pk)
        self.assertEqual(survivor.max_marks, 15)
        self.assertEqual(survivor.order, 3)
        self.assertFalse(ExamQuestionPart.objects.filter(pk=second.pk).exists())

    def test_a_plain_letter_beats_its_own_sub_part(self):
        """(c) + (c)(i) must not trip unique_together on the relabel."""
        plain = self.part('(c)', max_marks=5, order=1)
        self.part('(c) (i)', max_marks=10, order=2)
        self.merge('--apply')

        self.assertEqual(self.labels(), ['(c)'])
        self.assertEqual(ExamQuestionPart.objects.get().pk, plain.pk)

    def test_running_twice_changes_nothing_the_second_time(self):
        self.part('(c) (i)', max_marks=5, order=1)
        self.part('(c) (ii)', max_marks=10, order=2)
        self.merge('--apply')

        output = self.merge('--apply')
        self.assertEqual(ExamQuestionPart.objects.count(), 1)
        self.assertIn('0 to merge', output)

    def test_check_exits_non_zero_while_work_remains(self):
        self.part('(c) (i)')
        self.part('(c) (ii)')
        with self.assertRaises(SystemExit):
            self.merge('--check')

        self.merge('--apply')
        self.merge('--check')  # no longer raises


class DryRunTests(MergeTestBase):
    def test_nothing_is_written_without_apply(self):
        self.part('(c) (i)', max_marks=5, order=1)
        self.part('(c) (ii)', max_marks=10, order=2)

        output = self.merge()

        self.assertEqual(self.labels(), ['(c) (i)', '(c) (ii)'])
        self.assertEqual(ExamQuestionPart.objects.count(), 2)
        self.assertIn('Nothing was written', output)
        self.assertIn("'(c) (i)' + '(c) (ii)' -> (c)", output)

    def test_the_parsed_labels_are_printed_before_anything_happens(self):
        self.part('(c) (i)')
        output = self.merge()
        self.assertIn('Labels as parsed', output)
        self.assertIn("'(c) (i)'", output)


class MarksTests(MergeTestBase):
    def merge_pair(self, first_marks, second_marks, *extra):
        self.part('(c) (i)', max_marks=first_marks, order=1)
        self.part('(c) (ii)', max_marks=second_marks, order=2)
        output = self.merge('--apply', *extra)
        return ExamQuestionPart.objects.get(), output

    def test_marks_are_summed_when_every_sub_part_has_them(self):
        part, _ = self.merge_pair(10, 20)
        self.assertEqual(part.max_marks, 30)

    def test_a_blank_leaves_the_total_blank_rather_than_understated(self):
        """An understated maximum inflates every future score on the part."""
        part, output = self.merge_pair(10, None)
        self.assertIsNone(part.max_marks)
        self.assertIn('needs checking', output)

    def test_sum_partial_marks_takes_the_other_choice(self):
        part, _ = self.merge_pair(10, None, '--sum-partial-marks')
        self.assertEqual(part.max_marks, 10)


class CropTests(MergeTestBase):
    def test_every_crop_survives_in_reading_order(self):
        first = self.part('(c) (i)', order=1, solution_image=image('i.png'))
        second = self.part('(c) (ii)', order=2, solution_image=image('ii.png'))
        first_name, second_name = first.solution_image.name, second.solution_image.name

        self.merge('--apply')

        survivor = ExamQuestionPart.objects.get()
        self.assertEqual([i.name for i in survivor.solution_images],
                         [first_name, second_name])

    def test_the_file_changes_owner_rather_than_being_copied(self):
        """Deleting a row does not delete its file, so the name can move."""
        self.part('(c) (i)', order=1, solution_image=image('i.png'))
        second = self.part('(c) (ii)', order=2, solution_image=image('ii.png'))
        second_name = second.solution_image.name

        self.merge('--apply')

        extra = ExamPartSolutionImage.objects.get()
        self.assertEqual(extra.image.name, second_name)

    def test_a_sub_part_with_no_crop_does_not_leave_a_gap(self):
        self.part('(c) (i)', order=1)
        self.part('(c) (ii)', order=2, solution_image=image('ii.png'))

        self.merge('--apply')

        survivor = ExamQuestionPart.objects.get()
        self.assertEqual(len(survivor.solution_images), 1)
        self.assertFalse(survivor.extra_solution_images.exists())
        self.assertTrue(survivor.solution_image)


class CascadeTests(MergeTestBase):
    """Everything pointing at a deleted part cascades. Nothing may be lost."""

    def setUp(self):
        self.first = self.part('(c) (i)', order=1)
        self.second = self.part('(c) (ii)', order=2)
        self.attempt = ExamAttempt.objects.create(
            student=self.student, exam_paper=self.paper,
            attempt_mode='question_practice', total_marks_possible=300,
        )

    def test_an_attempt_on_a_deleted_sub_part_is_moved_not_lost(self):
        answer = ExamQuestionAttempt.objects.create(
            exam_attempt=self.attempt, question_part=self.second,
            student_answer='42', max_marks=10,
        )
        self.merge('--apply')

        answer.refresh_from_db()
        self.assertEqual(answer.question_part_id, self.first.pk)

    def test_a_homework_task_is_moved(self):
        from django.utils import timezone

        from homework.models import (
            HomeworkAssignment, HomeworkTask, TeacherProfile,
        )
        staff = User.objects.create_user('teacher', password='pw', is_staff=True)
        profile, _ = TeacherProfile.objects.get_or_create(
            user=staff, defaults={'display_name': 'Ms Teacher'})
        assignment = HomeworkAssignment.objects.create(
            teacher=profile, topic=self.topic, title='Integration',
            due_date=timezone.now() + timezone.timedelta(days=1),
        )
        task = HomeworkTask.objects.create(
            assignment=assignment, task_type='exam_part',
            exam_question_part=self.second, order=1,
        )
        self.merge('--apply')

        task.refresh_from_db()
        self.assertEqual(task.exam_question_part_id, self.first.pk)

    def test_a_work_photo_is_moved(self):
        from students.models import StudentProfile, WorkSubmission
        profile = StudentProfile.objects.get(user=self.student)
        submission = WorkSubmission.objects.create(
            student=profile, exam_question_part=self.second,
            image=image('work.png'),
        )
        self.merge('--apply')

        submission.refresh_from_db()
        self.assertEqual(submission.exam_question_part_id, self.first.pk)

    def test_the_dry_run_says_what_would_move(self):
        ExamQuestionAttempt.objects.create(
            exam_attempt=self.attempt, question_part=self.second,
            student_answer='42', max_marks=10,
        )
        self.assertIn('1 attempts', self.merge())
