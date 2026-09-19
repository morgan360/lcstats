"""Setting a single exam question part as homework: what the task says, where
it sends the student, and when it counts as done."""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Subject
from exam_papers.models import (
    ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionAttempt, ExamQuestionPart,
)
from homework.models import (
    HomeworkAssignment, HomeworkTask, StudentHomeworkProgress, TeacherProfile,
)
from interactive_lessons.models import Topic


class ExamPartTaskTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.integration = Topic.objects.create(name='Integration', subject=cls.maths, paper='p1')
        cls.functions = Topic.objects.create(name='Functions', subject=cls.maths, paper='p1')

        cls.paper = ExamPaper.objects.create(
            subject=cls.maths, year=2019, paper_type='p1',
            total_marks=300, is_published=True,
        )
        cls.question = ExamQuestion.objects.create(
            exam_paper=cls.paper, question_number=6, topic=cls.functions, total_marks=30,
        )
        cls.part_a = ExamQuestionPart.objects.create(
            question=cls.question, label='(a)', max_marks=10, order=1)
        cls.part_b = ExamQuestionPart.objects.create(
            question=cls.question, label='(b)', max_marks=20, order=2)
        cls.part_a.topic = cls.functions
        cls.part_a.save(update_fields=['topic'])
        cls.part_b.topic = cls.integration
        cls.part_b.save(update_fields=['topic'])

        cls.student = User.objects.create_user('student', password='pw')
        cls.staff = User.objects.create_user('teacher', password='pw', is_staff=True)
        cls.teacher = TeacherProfile.objects.create(user=cls.staff, display_name='Ms Teacher')
        cls.assignment = HomeworkAssignment.objects.create(
            teacher=cls.teacher, topic=cls.integration, title='Integration week 1',
            due_date=timezone.now() + timezone.timedelta(days=1), is_published=True,
        )

    def task(self, part=None):
        return HomeworkTask.objects.create(
            assignment=self.assignment, task_type='exam_part',
            exam_question_part=part or self.part_b,
        )


class TaskContentTests(ExamPartTaskTestBase):
    def test_display_names_the_paper_question_part_and_topic(self):
        self.assertEqual(
            self.task().get_content_display(),
            '[Maths] 2019 Paper 1 - Q6(b) - Integration',
        )

    def test_url_opens_that_part(self):
        task = self.task()
        self.assertEqual(
            task.get_content_url(),
            reverse('exam_papers:practise_part', args=[self.part_b.id]),
        )

    def test_a_part_task_needs_a_part(self):
        task = HomeworkTask(assignment=self.assignment, task_type='exam_part')
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_other_task_types_drop_the_part(self):
        task = HomeworkTask(assignment=self.assignment, task_type='custom',
                            instructions='Text 5, Q1-10', exam_question_part=self.part_b)
        task.save()
        self.assertIsNone(task.exam_question_part)


class AutoCompletionTests(ExamPartTaskTestBase):
    def attempt(self, part):
        exam_attempt = ExamAttempt.objects.create(
            student=self.student, exam_paper=self.paper,
            attempt_mode='question_practice', total_marks_possible=300,
        )
        ExamQuestionAttempt.objects.create(
            exam_attempt=exam_attempt, question_part=part,
            student_answer='x', max_marks=part.max_marks,
        )

    def progress(self, task):
        return StudentHomeworkProgress.objects.create(
            student=self.student, assignment=self.assignment, task=task)

    def test_a_sibling_part_does_not_complete_the_task(self):
        progress = self.progress(self.task())
        self.attempt(self.part_a)
        self.assertFalse(progress.check_auto_completion())
        self.assertFalse(progress.is_completed)

    def test_attempting_the_set_part_completes_it(self):
        progress = self.progress(self.task())
        self.attempt(self.part_b)
        self.assertTrue(progress.check_auto_completion())
        self.assertTrue(progress.is_completed)


class PractisePartTests(ExamPartTaskTestBase):
    def setUp(self):
        self.client.force_login(self.student)

    def test_one_attempt_is_created_and_then_reused(self):
        url = reverse('exam_papers:practise_part', args=[self.part_b.id])
        first = self.client.get(url)
        second = self.client.get(url)

        self.assertEqual(first['Location'], second['Location'])
        self.assertTrue(first['Location'].endswith(f'?part={self.part_b.id}'))
        self.assertEqual(ExamAttempt.objects.filter(student=self.student).count(), 1)

    def test_unpublished_paper_is_not_practisable(self):
        self.paper.is_published = False
        self.paper.save(update_fields=['is_published'])
        response = self.client.get(reverse('exam_papers:practise_part', args=[self.part_b.id]))
        self.assertEqual(response.status_code, 404)


class PickerTests(ExamPartTaskTestBase):
    def setUp(self):
        self.client.force_login(self.staff)
        self.url = reverse('homework:pick_exam_parts', args=[self.assignment.id])

    def test_students_cannot_open_it(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_lists_only_the_parts_on_the_chosen_topic(self):
        response = self.client.get(self.url, {'topic': self.integration.id})
        matching = [p for q in response.context['questions'] for p in q.matching_parts]
        self.assertEqual(matching, [self.part_b])

    def test_ticked_parts_become_tasks_and_are_not_doubled_up(self):
        self.client.post(self.url, {'part_ids': [self.part_b.id]})
        self.client.post(self.url, {'part_ids': [self.part_b.id, self.part_a.id]})

        tasks = HomeworkTask.objects.filter(assignment=self.assignment, task_type='exam_part')
        self.assertEqual(
            sorted(t.exam_question_part_id for t in tasks),
            sorted([self.part_a.id, self.part_b.id]),
        )


class PickerReturnsToFormTests(ExamPartTaskTestBase):
    """The picker can run before an assignment exists, handing its ticks back to
    the form so an assignment and its parts are saved together."""

    def setUp(self):
        self.client.force_login(self.staff)

    def test_it_opens_without_an_assignment(self):
        response = self.client.get(
            reverse('homework:pick_exam_parts_unsaved'),
            {'topic': self.integration.id, 'return': 'form'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['assignment'])
        self.assertTrue(response.context['return_to_form'])
        self.assertContains(response, 'Add to the assignment form')

    def test_a_part_from_another_topic_still_validates(self):
        from homework.forms import ExamQuestionPartsTaskForm

        form = ExamQuestionPartsTaskForm(
            data={
                'assignment': self.assignment.id,
                'task_type': 'exam_part',
                'exam_question_part': self.part_a.id,  # Functions, not Integration
                'order': 0,
            },
            parent_assignment=self.assignment,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['exam_question_part'], self.part_a)

    def test_the_admin_form_carries_the_picker_link_and_its_script(self):
        admin = User.objects.create_superuser('admin', 'admin@example.com', 'pw')
        self.client.force_login(admin)
        response = self.client.get('/admin/homework/homeworkassignment/add/')
        self.assertContains(response, 'id="parts-picker-link"')
        self.assertContains(response, 'homework_parts_picker.js')
