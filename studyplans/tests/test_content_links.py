"""Naming and linking content, shared between homework tasks and plan items.

These assertions are deliberately the same shape as the ones in
homework/tests/test_exam_part_tasks.py: the point of the shared module is that
both models say exactly the same thing about the same row.
"""
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core import content_links
from core.models import Subject
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart
from flashcards.models import Flashcard, FlashcardSet
from homework.models import HomeworkAssignment, HomeworkTask, TeacherProfile
from interactive_lessons.models import Question, QuestionPart, Section, Topic
from quickkicks.models import QuickKick
from studyplans.models import StudyPlan, StudyPlanItem, StudyPlanWeek


class ContentLinkTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(
            name='Integration', subject=cls.maths, paper='p1')

        user = User.objects.create_user('ms_teacher', password='pw', is_staff=True)
        group, _ = Group.objects.get_or_create(name='Teachers')
        user.groups.add(group)
        cls.teacher, _ = TeacherProfile.objects.get_or_create(user=user)
        cls.student = User.objects.create_user('aoife', password='pw')

        cls.section = Section.objects.create(
            name='By parts', topic=cls.topic, order=1)
        cls.question_row = Question.objects.create(
            topic=cls.topic, section=cls.section, order=1)
        QuestionPart.objects.create(
            question=cls.question_row, label='(a)', prompt='p', answer='1',
            max_marks=5, order=1)

        cls.paper = ExamPaper.objects.create(
            subject=cls.maths, year=2019, paper_type='p1',
            total_marks=300, is_published=True)
        cls.exam_question = ExamQuestion.objects.create(
            exam_paper=cls.paper, question_number=6,
            topic=cls.topic, total_marks=30)
        cls.part = ExamQuestionPart.objects.create(
            question=cls.exam_question, label='(b)', max_marks=20,
            order=2, topic=cls.topic)

        cls.card_set = FlashcardSet.objects.create(
            topic=cls.topic, title='Terms', is_published=True)
        Flashcard.objects.create(
            flashcard_set=cls.card_set, front_text='q', back_text='a',
            distractor_1='x', distractor_2='y', distractor_3='z', order=1)

        cls.kick = QuickKick.objects.create(
            topic=cls.topic, title='Parts', content_type='geogebra',
            geogebra_code='abc', order=1)

        cls.today = timezone.localdate()
        cls.plan = StudyPlan.objects.create(
            student=cls.student, teacher=cls.teacher, subject=cls.maths,
            title='Plan', start_date=cls.today,
            deadline=cls.today + timedelta(days=14), status='active')
        cls.week = StudyPlanWeek.objects.create(
            plan=cls.plan, index=1, start_date=cls.today,
            end_date=cls.today + timedelta(days=6), minutes_budget=120)
        cls.assignment = HomeworkAssignment.objects.create(
            teacher=cls.teacher, topic=cls.topic, title='HW',
            due_date=timezone.now() + timedelta(days=7))

    def item(self, kind, **refs):
        return StudyPlanItem.objects.create(
            plan=self.plan, week=self.week, content_type=kind,
            available_from=self.today, due_date=self.today + timedelta(days=6),
            **refs)


class DisplayAndUrlTests(ContentLinkTestBase):

    def test_an_exam_part_is_named_the_way_a_teacher_says_it(self):
        item = self.item('exam_part', exam_question_part=self.part)
        self.assertEqual(item.get_content_display(),
                         '[Maths] 2019 Paper 1 - Q6(b) - Integration')

    def test_an_exam_part_links_straight_into_the_part(self):
        item = self.item('exam_part', exam_question_part=self.part)
        self.assertEqual(item.get_content_url(),
                         reverse('exam_papers:practise_part', args=[self.part.id]))

    def test_a_section_links_to_its_quiz_and_carries_the_subject(self):
        item = self.item('section', section=self.section)
        url = item.get_content_url()
        self.assertIn(f'/interactive/{self.topic.slug}/sections/', url)
        self.assertIn('?subject=maths', url)

    def test_every_kind_has_a_label_and_a_link(self):
        cases = [
            ('section', {'section': self.section}),
            ('exam_question', {'exam_question': self.exam_question}),
            ('exam_part', {'exam_question_part': self.part}),
            ('quickkick', {'quickkick': self.kick}),
            ('flashcard', {'flashcard_set': self.card_set}),
        ]
        for kind, refs in cases:
            item = self.item(kind, **refs)
            self.assertNotEqual(item.get_content_display(), 'Unknown task', kind)
            self.assertNotEqual(item.get_content_url(), '#', kind)

    def test_a_written_exercise_reads_back_its_own_text(self):
        item = self.item('custom', instructions='Read chapter 4')
        self.assertEqual(item.get_content_display(), 'Read chapter 4')


class AgreementWithHomeworkTests(ContentLinkTestBase):
    """The whole point of sharing the module: both models say the same thing."""

    def test_a_plan_item_and_a_homework_task_name_a_part_identically(self):
        task = HomeworkTask.objects.create(
            assignment=self.assignment, task_type='exam_part',
            exam_question_part=self.part)
        item = self.item('exam_part', exam_question_part=self.part)
        self.assertEqual(item.get_content_display(), task.get_content_display())
        self.assertEqual(item.get_content_url(), task.get_content_url())

    def test_they_agree_on_a_section_too(self):
        task = HomeworkTask.objects.create(
            assignment=self.assignment, task_type='section', section=self.section)
        item = self.item('section', section=self.section)
        self.assertEqual(item.get_content_display(), task.get_content_display())
        self.assertEqual(item.get_content_url(), task.get_content_url())


class ValidationTests(ContentLinkTestBase):

    def test_a_kind_without_its_own_row_is_refused(self):
        with self.assertRaises(ValidationError):
            self.item('exam_part')

    def test_a_written_exercise_needs_words(self):
        with self.assertRaises(ValidationError):
            self.item('custom', instructions='   ')

    def test_the_other_foreign_keys_are_cleared(self):
        item = self.item('exam_part', exam_question_part=self.part,
                         section=self.section)
        item.refresh_from_db()
        self.assertIsNone(item.section_id)
        self.assertEqual(item.exam_question_part_id, self.part.id)

    def test_a_week_from_another_plan_is_refused(self):
        # A draft, because a student may hold only one active plan; what is
        # under test here is the week/plan mismatch, not the status rule.
        other = StudyPlan.objects.create(
            student=self.student, teacher=self.teacher, subject=self.maths,
            title='Other', start_date=self.today,
            deadline=self.today + timedelta(days=7), status='draft')
        other_week = StudyPlanWeek.objects.create(
            plan=other, index=1, start_date=self.today,
            end_date=self.today + timedelta(days=6), minutes_budget=60)
        with self.assertRaises(ValidationError):
            StudyPlanItem.objects.create(
                plan=self.plan, week=other_week, content_type='section',
                section=self.section, available_from=self.today,
                due_date=self.today + timedelta(days=6))

    def test_validate_refs_reports_rather_than_raises(self):
        errors = content_links.validate_refs('flashcard', {})
        self.assertIn('flashcard_set', errors)
        self.assertEqual(content_links.validate_refs(
            'flashcard', {'flashcard_set': self.card_set}), {})
