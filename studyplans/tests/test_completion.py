"""When planned work counts as done -- and, above all, which work counts at all.

The rule that earns its keep here is the window: a plan set today must not mark
itself complete from practice the student did last term.
"""
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone

from core.models import Subject
from exam_papers.models import (
    ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionAttempt, ExamQuestionPart,
)
from flashcards.models import Flashcard, FlashcardAttempt, FlashcardSet
from homework.models import TeacherProfile
from interactive_lessons.models import Question, QuestionPart, Section, Topic
from quickkicks.models import QuickKick, QuickKickView
from students.models import QuestionAttempt
from studyplans.models import StudyPlan, StudyPlanGoal, StudyPlanItem, StudyPlanWeek
from studyplans.services import completion


def make_teacher(username):
    user = User.objects.create_user(username=username, password='pw', is_staff=True)
    group, _ = Group.objects.get_or_create(name='Teachers')
    user.groups.add(group)
    profile, _ = TeacherProfile.objects.get_or_create(user=user)
    return user, profile


class CompletionTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(
            name='Probability', subject=cls.maths, paper='p2')
        cls.teacher_user, cls.teacher = make_teacher('ms_teacher')
        cls.student = User.objects.create_user('aoife', password='pw')
        cls.profile = cls.student.studentprofile

        cls.section = Section.objects.create(
            name='Counting', topic=cls.topic, order=1)
        cls.questions = []
        for n in range(4):
            question = Question.objects.create(
                topic=cls.topic, section=cls.section, order=n)
            QuestionPart.objects.create(
                question=question, label='(a)', prompt='p', answer='1',
                max_marks=5, order=1)
            cls.questions.append(question)

        cls.paper = ExamPaper.objects.create(
            subject=cls.maths, year=2021, paper_type='p2',
            total_marks=300, is_published=True)
        cls.question = ExamQuestion.objects.create(
            exam_paper=cls.paper, question_number=3,
            topic=cls.topic, total_marks=25)
        cls.part = ExamQuestionPart.objects.create(
            question=cls.question, label='(a)', max_marks=10, order=1,
            topic=cls.topic)

        cls.card_set = FlashcardSet.objects.create(
            topic=cls.topic, title='Terms', is_published=True)
        cls.cards = [
            Flashcard.objects.create(
                flashcard_set=cls.card_set, front_text=f'q{n}', back_text='a',
                distractor_1='x', distractor_2='y', distractor_3='z', order=n)
            for n in range(5)
        ]

        cls.kick = QuickKick.objects.create(
            topic=cls.topic, title='Tree diagrams', content_type='geogebra',
            geogebra_code='abc123', order=1)

        cls.today = timezone.localdate()
        cls.plan = StudyPlan.objects.create(
            student=cls.student, teacher=cls.teacher, subject=cls.maths,
            title='Plan', start_date=cls.today,
            deadline=cls.today + timedelta(days=14), status='active')
        cls.goal = StudyPlanGoal.objects.create(plan=cls.plan, topic=cls.topic)
        cls.week = StudyPlanWeek.objects.create(
            plan=cls.plan, index=1, start_date=cls.today,
            end_date=cls.today + timedelta(days=6), minutes_budget=120)

    def item(self, kind, **refs):
        return StudyPlanItem.objects.create(
            plan=self.plan, week=self.week, goal=self.goal, content_type=kind,
            available_from=self.today, due_date=self.today + timedelta(days=6),
            **refs)

    def practice_attempt(self, question, score, when=None):
        return QuestionAttempt.objects.create(
            student=self.profile, question=question,
            question_part=question.parts.first(),
            student_answer='x', score_awarded=score,
            is_correct=score >= 50,
            attempted_at=when or timezone.now())

    def exam_attempt(self, marks, when=None):
        attempt, _ = ExamAttempt.objects.get_or_create(
            student=self.student, exam_paper=self.paper,
            attempt_mode='question_practice')
        row = ExamQuestionAttempt.objects.create(
            exam_attempt=attempt, question_part=self.part,
            student_answer='x', marks_awarded=marks, max_marks=10)
        if when is not None:
            ExamQuestionAttempt.objects.filter(pk=row.pk).update(submitted_at=when)
        return row


class TheWindowTests(CompletionTestBase):

    def test_work_done_before_the_item_was_set_does_not_complete_it(self):
        """The headline guard: no plan marks itself done from last term's work."""
        long_ago = timezone.now() - timedelta(days=60)
        for question in self.questions:
            self.practice_attempt(question, 100, when=long_ago)

        item = self.item('section', section=self.section)
        outcome = completion.outcome_for(item)
        self.assertEqual(outcome.status, 'pending')

        completion.persist([item])
        item.refresh_from_db()
        self.assertEqual(item.status, 'pending')

    def test_the_same_work_done_after_it_was_set_does_complete_it(self):
        for question in self.questions:
            self.practice_attempt(question, 100)
        item = self.item('section', section=self.section)
        completion.persist([item])
        item.refresh_from_db()
        self.assertEqual(item.status, 'done')

    def test_an_exam_attempt_before_the_window_does_not_count(self):
        self.exam_attempt(10, when=timezone.now() - timedelta(days=30))
        item = self.item('exam_part', exam_question_part=self.part)
        self.assertEqual(completion.outcome_for(item).status, 'pending')


class SectionCompletionTests(CompletionTestBase):

    def test_one_question_out_of_four_is_not_a_finished_section(self):
        self.practice_attempt(self.questions[0], 100)
        item = self.item('section', section=self.section)
        self.assertEqual(completion.outcome_for(item).status, 'attempted')

    def test_most_of_the_section_at_a_passing_standard_is_done(self):
        for question in self.questions[:3]:
            self.practice_attempt(question, 80)
        item = self.item('section', section=self.section)
        self.assertEqual(completion.outcome_for(item).status, 'done')

    def test_attempting_every_question_badly_is_not_done(self):
        for question in self.questions:
            self.practice_attempt(question, 10)
        item = self.item('section', section=self.section)
        outcome = completion.outcome_for(item)
        self.assertEqual(outcome.status, 'attempted',
                         "wrong answers should not finish a section")


class ExamPartCompletionTests(CompletionTestBase):

    def test_half_marks_finishes_an_exam_part(self):
        self.exam_attempt(5)
        item = self.item('exam_part', exam_question_part=self.part)
        self.assertEqual(completion.outcome_for(item).status, 'done')

    def test_a_poor_attempt_is_started_but_not_done(self):
        self.exam_attempt(2)
        item = self.item('exam_part', exam_question_part=self.part)
        self.assertEqual(completion.outcome_for(item).status, 'attempted')


class FlashcardCompletionTests(CompletionTestBase):

    def test_opening_a_set_completes_nothing(self):
        """Opening a set creates a row per card, which is not evidence."""
        for card in self.cards:
            FlashcardAttempt.objects.create(
                student=self.student, flashcard=card, mastery_level='new')
        item = self.item('flashcard', flashcard_set=self.card_set)
        self.assertEqual(completion.outcome_for(item).status, 'pending')

    def test_knowing_most_of_the_cards_is_done(self):
        now = timezone.now()
        for card in self.cards[:4]:
            FlashcardAttempt.objects.create(
                student=self.student, flashcard=card, mastery_level='know',
                last_answered_at=now)
        FlashcardAttempt.objects.create(
            student=self.student, flashcard=self.cards[4], mastery_level='learning',
            last_answered_at=now)
        item = self.item('flashcard', flashcard_set=self.card_set)
        self.assertEqual(completion.outcome_for(item).status, 'done')

    def test_knowing_only_some_is_started(self):
        now = timezone.now()
        FlashcardAttempt.objects.create(
            student=self.student, flashcard=self.cards[0],
            mastery_level='know', last_answered_at=now)
        item = self.item('flashcard', flashcard_set=self.card_set)
        self.assertEqual(completion.outcome_for(item).status, 'attempted')


class QuickKickCompletionTests(CompletionTestBase):

    def test_watching_a_quickflick_with_a_question_is_not_enough(self):
        QuickKickView.objects.create(user=self.student, quickkick=self.kick)
        self.kick.question = self.questions[0]
        self.kick.save()
        item = self.item('quickkick', quickkick=self.kick)
        self.assertEqual(completion.outcome_for(item).status, 'attempted')

    def test_answering_its_question_finishes_it(self):
        self.kick.question = self.questions[0]
        self.kick.save()
        QuickKickView.objects.create(
            user=self.student, quickkick=self.kick, answer_submitted=True,
            answer_correct=True, score_awarded=100,
            last_attempt_at=timezone.now())
        item = self.item('quickkick', quickkick=self.kick)
        self.assertEqual(completion.outcome_for(item).status, 'done')

    def test_a_quickflick_with_no_question_is_done_once_watched(self):
        QuickKickView.objects.create(user=self.student, quickkick=self.kick)
        item = self.item('quickkick', quickkick=self.kick)
        self.assertEqual(completion.outcome_for(item).status, 'done')


class PersistTests(CompletionTestBase):

    def test_a_written_exercise_is_never_completed_automatically(self):
        item = self.item('custom', instructions='Read chapter 4')
        completion.persist([item])
        item.refresh_from_db()
        self.assertEqual(item.status, 'pending')

    def test_running_it_twice_changes_nothing_the_second_time(self):
        self.exam_attempt(9)
        item = self.item('exam_part', exam_question_part=self.part)
        first = completion.persist([item])
        self.assertEqual(len(first), 1)
        item.refresh_from_db()
        completed_at = item.completed_at

        second = completion.persist([item])
        self.assertEqual(second, [])
        item.refresh_from_db()
        self.assertEqual(item.completed_at, completed_at)

    def test_a_finished_item_cannot_be_undone_by_a_later_bad_attempt(self):
        self.exam_attempt(9)
        item = self.item('exam_part', exam_question_part=self.part)
        completion.persist([item])
        self.exam_attempt(0)
        completion.persist([item])
        item.refresh_from_db()
        self.assertEqual(item.status, 'done')

    def test_it_records_why_an_item_counted_as_done(self):
        for question in self.questions[:3]:
            self.practice_attempt(question, 90)
        item = self.item('section', section=self.section)
        completion.persist([item])
        item.refresh_from_db()
        self.assertIn('of 4 questions', item.evidence_note)
