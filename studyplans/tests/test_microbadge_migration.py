"""The migration that turns a week-based plan into MicroBadges.

It runs once, on production's real plans, so it is tested on the shape those
plans actually have: items spread over weeks, some done, some skipped.
"""
import importlib
from datetime import timedelta

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from core.models import Subject
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart
from homework.models import TeacherProfile
from interactive_lessons.models import Topic
from studyplans.models import (
    StudyPlan, StudyPlanGoal, StudyPlanItem, StudyPlanMicroBadge, StudyPlanWeek,
)

migration = importlib.import_module(
    'studyplans.migrations.0007_weeks_into_microbadges')


class WeeksIntoMicroBadgesTests(TestCase):

    def setUp(self):
        maths = Subject.objects.get(slug='maths')
        topic = Topic.objects.create(name='Integration', subject=maths, paper='p1')
        teacher = User.objects.create_user('ms_teacher', password='pw', is_staff=True)
        profile, _ = TeacherProfile.objects.get_or_create(user=teacher)
        student = User.objects.create_user('aoife', password='pw')
        paper = ExamPaper.objects.create(subject=maths, year=2020, paper_type='p1',
                                         total_marks=300, is_published=True)
        question = ExamQuestion.objects.create(exam_paper=paper, question_number=6,
                                               topic=topic, total_marks=100)
        parts = [ExamQuestionPart.objects.create(
                     question=question, label=f'({chr(97 + n)})', max_marks=10,
                     order=n, topic=topic) for n in range(8)]

        self.today = timezone.localdate()
        self.plan = StudyPlan.objects.create(
            student=student, teacher=profile, subject=maths, title='Old style',
            start_date=self.today - timedelta(days=14),
            deadline=self.today + timedelta(days=42), status='active')
        self.goal = StudyPlanGoal.objects.create(plan=self.plan, topic=topic)
        weeks = [StudyPlanWeek.objects.create(
                     plan=self.plan, index=n + 1,
                     start_date=self.plan.start_date + timedelta(days=7 * n),
                     end_date=self.plan.start_date + timedelta(days=7 * n + 6),
                     minutes_budget=120) for n in range(3)]
        # Two done in week 1, one skipped, the rest pending in weeks 2 and 3.
        statuses = ['done', 'done', 'skipped', 'pending', 'pending',
                    'pending', 'pending', 'pending']
        self.items = []
        for n, (part, status) in enumerate(zip(parts, statuses)):
            week = weeks[min(2, n // 3)]
            self.items.append(StudyPlanItem.objects.create(
                plan=self.plan, week=week, goal=self.goal,
                content_type='exam_part', exam_question_part=part,
                estimated_minutes=5, order=n, status=status,
                completed_at=timezone.now() if status == 'done' else None,
                available_from=self.plan.start_date, due_date=week.end_date))

    def run_migration(self):
        migration.forwards(apps, None)

    def test_every_goal_gets_ten_core_microbadges(self):
        self.run_migration()
        badges = StudyPlanMicroBadge.objects.filter(goal=self.goal)
        self.assertEqual(badges.count(), 10)
        self.assertEqual(sorted(b.number for b in badges), list(range(1, 11)))

    def test_items_keep_their_order_and_skipped_ones_stay_out(self):
        self.run_migration()
        placed = [i for i in StudyPlanItem.objects.filter(goal=self.goal)
                  .select_related('micro_badge').order_by('order')
                  if i.micro_badge]
        numbers = [i.micro_badge.number for i in placed]
        self.assertEqual(numbers, sorted(numbers))
        skipped = StudyPlanItem.objects.get(id=self.items[2].id)
        self.assertIsNone(skipped.micro_badge)
        self.assertEqual(skipped.status, 'skipped')

    def test_microbadges_already_done_are_earned(self):
        self.run_migration()
        first = StudyPlanMicroBadge.objects.get(goal=self.goal, number=1)
        self.assertEqual([i.status for i in first.items.all()], ['done'])
        self.assertIsNotNone(first.earned_at)
        self.assertFalse(StudyPlanMicroBadge.objects.filter(
            goal=self.goal, number=3).exclude(earned_at=None).exists())

    def test_nothing_is_deleted_and_running_twice_is_harmless(self):
        self.run_migration()
        self.run_migration()
        self.assertEqual(StudyPlanMicroBadge.objects.filter(goal=self.goal).count(), 10)
        self.assertEqual(StudyPlanItem.objects.filter(goal=self.goal).count(), 8)
        self.assertEqual(self.plan.weeks.count(), 3)

    def test_due_dates_follow_the_microbadge_but_never_before_opening(self):
        self.run_migration()
        for item in StudyPlanItem.objects.filter(goal=self.goal).exclude(
                micro_badge=None).select_related('micro_badge'):
            self.assertEqual(item.due_date,
                             max(item.micro_badge.target_date, item.available_from))
