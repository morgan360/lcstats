"""The nightly run: what it moves, what it opens, and what it must leave alone.

The two rules under test that matter most are that a teacher's own choices are
never rearranged, and that running it twice does nothing the second time.
"""
from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.models import Subject
from exam_papers.models import (
    ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionAttempt, ExamQuestionPart,
)
from homework.models import TeacherProfile
from interactive_lessons.models import Question, QuestionPart, Section, Topic
from studyplans import constants
from studyplans.models import (
    StudyPlan, StudyPlanCheckpoint, StudyPlanGoal, StudyPlanItem, StudyPlanWeek,
)
from studyplans.services import checkpoints as checkpoint_service
from studyplans.services import nightly


def make_teacher(username):
    user = User.objects.create_user(username=username, password='pw', is_staff=True)
    group, _ = Group.objects.get_or_create(name='Teachers')
    user.groups.add(group)
    profile, _ = TeacherProfile.objects.get_or_create(user=user)
    return user, profile


class NightlyTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(
            name='Integration', subject=cls.maths, paper='p1')
        cls.teacher_user, cls.teacher = make_teacher('ms_teacher')
        cls.student = User.objects.create_user('aoife', password='pw')
        cls.profile = cls.student.studentprofile

        cls.parts = []
        for year in (2017, 2018, 2019, 2020, 2021, 2022):
            paper = ExamPaper.objects.create(
                subject=cls.maths, year=year, paper_type='p1',
                total_marks=300, is_published=True)
            question = ExamQuestion.objects.create(
                exam_paper=paper, question_number=6,
                topic=cls.topic, total_marks=20)
            for n, label in enumerate(['(a)', '(b)'], start=1):
                cls.parts.append(ExamQuestionPart.objects.create(
                    question=question, label=label, max_marks=10,
                    order=n, topic=cls.topic))

        cls.section = Section.objects.create(
            name='By parts', topic=cls.topic, order=1)
        for n in range(2):
            question = Question.objects.create(
                topic=cls.topic, section=cls.section, order=n)
            QuestionPart.objects.create(
                question=question, label='(a)', prompt='p', answer='1',
                max_marks=5, order=1)

    def setUp(self):
        self.today = timezone.localdate()
        self.plan = StudyPlan.objects.create(
            student=self.student, teacher=self.teacher, subject=self.maths,
            title='Plan', start_date=self.today - timedelta(days=7),
            deadline=self.today + timedelta(days=21), status='active')
        self.goal = StudyPlanGoal.objects.create(
            plan=self.plan, topic=self.topic, target_mastery=75,
            checkpoint_size=2)
        self.last_week = StudyPlanWeek.objects.create(
            plan=self.plan, index=1,
            start_date=self.today - timedelta(days=self.today.weekday() + 7),
            end_date=self.today - timedelta(days=self.today.weekday() + 1),
            minutes_budget=120)
        self.this_week = StudyPlanWeek.objects.create(
            plan=self.plan, index=2,
            start_date=self.today - timedelta(days=self.today.weekday()),
            end_date=self.today + timedelta(days=6 - self.today.weekday()),
            minutes_budget=120)

    def add_item(self, week, *, origin='generated', status='pending', part=None):
        return StudyPlanItem.objects.create(
            plan=self.plan, week=week, goal=self.goal,
            content_type='exam_part',
            exam_question_part=part or self.parts[-1],
            estimated_minutes=5, origin=origin, status=status,
            available_from=week.start_date, due_date=week.end_date)

    def checkpoint(self, parts=None, status='locked'):
        return checkpoint_service.create_checkpoint(
            self.goal, parts=parts or self.parts[:2], status=status)

    def sit(self, checkpoint, marks_each):
        attempt, _ = ExamAttempt.objects.get_or_create(
            student=self.student, exam_paper=self.parts[0].question.exam_paper,
            attempt_mode='question_practice')
        for part in checkpoint.parts.select_related('exam_question_part'):
            ExamQuestionAttempt.objects.create(
                exam_attempt=attempt, question_part=part.exam_question_part,
                student_answer='x', marks_awarded=marks_each, max_marks=10)


class UnlockingTests(NightlyTestBase):

    def test_a_checkpoint_opens_once_the_work_is_mostly_done(self):
        cp = self.checkpoint()
        for _ in range(4):
            self.add_item(self.this_week, status='done')
        self.add_item(self.this_week, status='pending')

        nightly.unlock_due_checkpoints(self.plan)
        cp.refresh_from_db()
        self.assertEqual(cp.status, 'ready')
        self.assertIsNotNone(cp.unlocked_at)

    def test_it_stays_shut_while_there_is_work_left(self):
        cp = self.checkpoint()
        self.add_item(self.this_week, status='done')
        for _ in range(3):
            self.add_item(self.this_week, status='pending')

        nightly.unlock_due_checkpoints(self.plan)
        cp.refresh_from_db()
        self.assertEqual(cp.status, 'locked')

    def test_a_mastered_goal_opens_nothing_further(self):
        self.checkpoint()
        self.goal.mastered_at = timezone.now()
        self.goal.mastery_score = 90
        self.goal.save(update_fields=['mastered_at', 'mastery_score'])
        self.assertEqual(nightly.unlock_due_checkpoints(self.plan), [])


class GradingTests(NightlyTestBase):

    def test_passing_masters_the_goal_and_retires_its_leftover_work(self):
        cp = self.checkpoint(status='ready')
        leftover = self.add_item(self.this_week)
        self.sit(cp, 9)

        nightly.grade_sat_checkpoints(self.plan)
        cp.refresh_from_db()
        self.goal.refresh_from_db()
        leftover.refresh_from_db()

        self.assertEqual(cp.status, 'passed')
        self.assertIsNotNone(self.goal.mastered_at)
        self.assertEqual(leftover.status, 'skipped')

    def test_failing_sets_a_fresh_checkpoint_on_different_parts(self):
        first = self.checkpoint(parts=self.parts[:2], status='ready')
        self.sit(first, 2)

        nightly.grade_sat_checkpoints(self.plan)
        first.refresh_from_db()
        self.assertEqual(first.status, 'failed')

        second = self.goal.checkpoints.filter(status='ready').exclude(
            id=first.id).first()
        self.assertIsNotNone(second, "a new checkpoint should be waiting")
        first_parts = {p.exam_question_part_id for p in first.parts.all()}
        second_parts = {p.exam_question_part_id for p in second.parts.all()}
        self.assertFalse(first_parts & second_parts,
                         "the retry must use parts they have not seen")

    def test_failing_adds_more_practice(self):
        cp = self.checkpoint(status='ready')
        self.sit(cp, 1)
        before = self.plan.items.count()
        nightly.grade_sat_checkpoints(self.plan)
        self.assertGreater(self.plan.items.count(), before)
        self.assertTrue(self.plan.items.filter(origin='revisit').exists())

    def test_a_teacher_chosen_item_survives_a_pass(self):
        cp = self.checkpoint(status='ready')
        mine = self.add_item(self.this_week, origin='teacher')
        self.sit(cp, 10)
        nightly.grade_sat_checkpoints(self.plan)
        mine.refresh_from_db()
        self.assertEqual(mine.status, 'pending',
                         "the plan must not retire a teacher's own choice")


class CarryForwardTests(NightlyTestBase):

    def test_unfinished_work_moves_into_this_week(self):
        stale = self.add_item(self.last_week)
        carried = nightly.carry_forward(self.plan, self.today)
        stale.refresh_from_db()
        self.assertEqual(len(carried), 1)
        self.assertEqual(stale.week_id, self.this_week.id)
        self.assertEqual(stale.carried_over_count, 1)

    def test_a_teacher_chosen_item_is_never_moved(self):
        mine = self.add_item(self.last_week, origin='teacher')
        nightly.carry_forward(self.plan, self.today)
        mine.refresh_from_db()
        self.assertEqual(mine.week_id, self.last_week.id)

    def test_work_the_student_has_started_is_left_where_it_is(self):
        started = self.add_item(self.last_week)
        started.started_at = timezone.now()
        started.save(update_fields=['started_at'])
        nightly.carry_forward(self.plan, self.today)
        started.refresh_from_db()
        self.assertEqual(started.week_id, self.last_week.id)

    def test_after_enough_carries_the_teacher_is_told_instead(self):
        stale = self.add_item(self.last_week)
        stale.carried_over_count = constants.MAX_CARRY_OVERS
        stale.save(update_fields=['carried_over_count'])

        carried = nightly.carry_forward(self.plan, self.today)
        stale.refresh_from_db()
        self.assertEqual(carried, [])
        self.assertTrue(stale.needs_teacher_attention)
        self.assertEqual(stale.week_id, self.last_week.id)


class WholeRunTests(NightlyTestBase):

    def test_running_it_twice_changes_nothing_the_second_time(self):
        cp = self.checkpoint(status='ready')
        self.add_item(self.last_week)
        self.sit(cp, 9)

        nightly.run_for_plan(self.plan, self.today)
        snapshot = sorted(
            StudyPlanItem.objects.filter(plan=self.plan)
            .values_list('id', 'status', 'week_id', 'carried_over_count'))
        checkpoint_snapshot = sorted(
            StudyPlanCheckpoint.objects.filter(goal__plan=self.plan)
            .values_list('id', 'status', 'score'))

        second = nightly.run_for_plan(self.plan, self.today)
        self.assertEqual(
            sorted(StudyPlanItem.objects.filter(plan=self.plan)
                   .values_list('id', 'status', 'week_id', 'carried_over_count')),
            snapshot)
        self.assertEqual(
            sorted(StudyPlanCheckpoint.objects.filter(goal__plan=self.plan)
                   .values_list('id', 'status', 'score')),
            checkpoint_snapshot)
        self.assertEqual(second['graded'], 0)

    def test_a_locked_plan_is_left_alone(self):
        self.plan.is_locked = True
        self.plan.save(update_fields=['is_locked'])
        stale = self.add_item(self.last_week)
        nightly.run_for_plan(self.plan, self.today)
        stale.refresh_from_db()
        self.assertEqual(stale.week_id, self.last_week.id)

    def test_a_draft_plan_is_left_alone(self):
        self.plan.status = 'draft'
        self.plan.save(update_fields=['status'])
        stale = self.add_item(self.last_week)
        nightly.run_for_plan(self.plan, self.today)
        stale.refresh_from_db()
        self.assertEqual(stale.week_id, self.last_week.id)

    def test_the_plan_closes_once_every_topic_is_mastered(self):
        cp = self.checkpoint(status='ready')
        self.sit(cp, 10)
        nightly.run_for_plan(self.plan, self.today)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, 'completed')


class CommandTests(NightlyTestBase):

    def test_dry_run_writes_nothing(self):
        cp = self.checkpoint(status='ready')
        stale = self.add_item(self.last_week)
        self.sit(cp, 9)

        out = StringIO()
        call_command('run_study_plans', '--dry-run', stdout=out)

        cp.refresh_from_db()
        stale.refresh_from_db()
        self.plan.refresh_from_db()
        self.assertEqual(cp.status, 'ready')
        self.assertEqual(stale.week_id, self.last_week.id)
        self.assertIsNone(self.plan.last_checked_at)
        self.assertIn('nothing will be written', out.getvalue())

    def test_it_marks_and_carries_when_run_for_real(self):
        cp = self.checkpoint(status='ready')
        self.add_item(self.last_week)
        self.sit(cp, 9)

        out = StringIO()
        call_command('run_study_plans', stdout=out)
        cp.refresh_from_db()
        self.assertEqual(cp.status, 'passed')

    def test_it_can_be_limited_to_one_student(self):
        other = User.objects.create_user('brian', password='pw')
        other_plan = StudyPlan.objects.create(
            student=other, teacher=self.teacher, subject=self.maths,
            title='Other', start_date=self.today,
            deadline=self.today + timedelta(days=14), status='active')

        out = StringIO()
        call_command('run_study_plans', '--student', 'brian', stdout=out)
        self.assertIn('1 active plan', out.getvalue())
