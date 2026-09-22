"""The nightly run: what it awards, what it opens, and what it must leave alone.

The rules under test that matter most are that a MicroBadge, once earned, is
never taken back, that the Badge Test waits for all ten, and that running it
twice does nothing the second time.
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
    StudyPlan, StudyPlanCheckpoint, StudyPlanGoal, StudyPlanItem,
    StudyPlanMicroBadge,
)
from studyplans.services import checkpoints as checkpoint_service
from studyplans.services import microbadges, nightly


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
        self.badges = [
            StudyPlanMicroBadge.objects.create(
                goal=self.goal, number=n, kind='core', target_date=target)
            for n, target in enumerate(microbadges.target_dates(
                self.plan.start_date, self.plan.deadline), start=1)
        ]

    def add_item(self, badge, *, origin='generated', status='pending', part=None):
        return StudyPlanItem.objects.create(
            plan=self.plan, goal=self.goal, micro_badge=badge,
            content_type='exam_part',
            exam_question_part=part or self.parts[-1],
            estimated_minutes=5, origin=origin, status=status,
            completed_at=timezone.now() if status == 'done' else None,
            available_from=self.plan.start_date,
            due_date=max(badge.target_date, self.plan.start_date))

    def earn(self, badges):
        for badge in badges:
            badge.earned_at = timezone.now()
            badge.save(update_fields=['earned_at'])

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


class AwardingTests(NightlyTestBase):

    def test_a_microbadge_is_earned_when_all_its_items_are_done(self):
        self.add_item(self.badges[0], status='done')
        self.add_item(self.badges[0], status='done')
        earned = nightly.award_microbadges(self.plan)
        self.assertEqual([b.id for b in earned], [self.badges[0].id])
        self.badges[0].refresh_from_db()
        self.assertIsNotNone(self.badges[0].earned_at)
        self.assertTrue(self.plan.events.filter(kind='microbadge_earned').exists())

    def test_one_item_left_keeps_it_unearned(self):
        self.add_item(self.badges[0], status='done')
        self.add_item(self.badges[0], status='pending')
        self.assertEqual(nightly.award_microbadges(self.plan), [])

    def test_a_removed_item_does_not_hold_it_back(self):
        self.add_item(self.badges[0], status='done')
        self.add_item(self.badges[0], status='skipped')
        self.assertEqual(len(nightly.award_microbadges(self.plan)), 1)

    def test_an_empty_microbadge_is_never_earned_on_its_own(self):
        self.assertEqual(nightly.award_microbadges(self.plan), [])

    def test_unticking_an_item_never_takes_it_back(self):
        item = self.add_item(self.badges[0], status='done')
        nightly.award_microbadges(self.plan)
        item.status = 'pending'
        item.save()
        nightly.award_microbadges(self.plan)
        self.badges[0].refresh_from_db()
        self.assertIsNotNone(self.badges[0].earned_at)

    def test_a_teacher_can_award_one_by_hand(self):
        self.assertTrue(microbadges.earn(self.badges[3], by_teacher=True))
        self.badges[3].refresh_from_db()
        self.assertTrue(self.badges[3].earned_by_teacher)
        self.assertFalse(microbadges.earn(self.badges[3], by_teacher=True))


class UnlockingTests(NightlyTestBase):

    def test_the_badge_test_opens_once_all_ten_are_earned(self):
        cp = self.checkpoint()
        self.earn(self.badges)
        nightly.unlock_due_checkpoints(self.plan)
        cp.refresh_from_db()
        self.assertEqual(cp.status, 'ready')
        self.assertIsNotNone(cp.unlocked_at)

    def test_nine_of_ten_is_not_enough(self):
        cp = self.checkpoint()
        self.earn(self.badges[:9])
        nightly.unlock_due_checkpoints(self.plan)
        cp.refresh_from_db()
        self.assertEqual(cp.status, 'locked')

    def test_a_mastered_goal_opens_nothing_further(self):
        self.checkpoint()
        self.earn(self.badges)
        self.goal.mastered_at = timezone.now()
        self.goal.mastery_score = 90
        self.goal.save(update_fields=['mastered_at', 'mastery_score'])
        self.assertEqual(nightly.unlock_due_checkpoints(self.plan), [])


class GradingTests(NightlyTestBase):

    def test_passing_masters_the_goal_and_retires_its_leftover_work(self):
        cp = self.checkpoint(status='ready')
        leftover = self.add_item(self.badges[9])
        self.sit(cp, 9)

        nightly.grade_sat_checkpoints(self.plan)
        cp.refresh_from_db()
        self.goal.refresh_from_db()
        leftover.refresh_from_db()

        self.assertEqual(cp.status, 'passed')
        self.assertIsNotNone(self.goal.mastered_at)
        self.assertEqual(leftover.status, 'skipped')

    def test_failing_adds_a_retry_microbadge_of_fresh_practice(self):
        cp = self.checkpoint(status='ready')
        self.sit(cp, 1)
        nightly.grade_sat_checkpoints(self.plan)

        retry = self.goal.micro_badges.get(kind='retry')
        self.assertEqual(retry.number, 11)
        items = list(retry.items.all())
        self.assertTrue(items)
        self.assertTrue(all(i.origin == 'revisit' for i in items))

    def test_the_next_round_waits_for_the_retry_microbadge(self):
        first = self.checkpoint(parts=self.parts[:2], status='ready')
        self.sit(first, 2)
        nightly.grade_sat_checkpoints(self.plan)
        first.refresh_from_db()
        self.assertEqual(first.status, 'failed')

        second = self.goal.checkpoints.exclude(id=first.id).get()
        self.assertEqual(second.status, 'locked')
        first_parts = {p.exam_question_part_id for p in first.parts.all()}
        second_parts = {p.exam_question_part_id for p in second.parts.all()}
        self.assertFalse(first_parts & second_parts,
                         "the retry must use parts they have not seen")

        nightly.unlock_due_checkpoints(self.plan)
        second.refresh_from_db()
        self.assertEqual(second.status, 'locked')

        retry = self.goal.micro_badges.get(kind='retry')
        retry.items.update(status='done')
        nightly.award_microbadges(self.plan)
        nightly.unlock_due_checkpoints(self.plan)
        second.refresh_from_db()
        self.assertEqual(second.status, 'ready')

    def test_with_nothing_fresh_to_practise_the_next_round_opens_at_once(self):
        # Every candidate already on the plan, so a retry would be empty.
        for part in self.parts[4:]:
            self.add_item(self.badges[0], part=part)
        StudyPlanItem.objects.create(
            plan=self.plan, goal=self.goal, micro_badge=self.badges[1],
            content_type='section', section=self.section, estimated_minutes=5,
            available_from=self.plan.start_date,
            due_date=max(self.badges[1].target_date, self.plan.start_date))
        first = self.checkpoint(parts=self.parts[:2], status='ready')
        checkpoint_service.create_checkpoint(
            self.goal, parts=self.parts[2:4], round_number=2, status='locked')
        self.sit(first, 2)
        nightly.grade_sat_checkpoints(self.plan)
        self.assertFalse(self.goal.micro_badges.filter(kind='retry').exists())
        self.assertTrue(self.goal.checkpoints.filter(round=2, status='ready').exists())

    def test_a_teacher_chosen_item_survives_a_pass(self):
        cp = self.checkpoint(status='ready')
        mine = self.add_item(self.badges[9], origin='teacher')
        self.sit(cp, 10)
        nightly.grade_sat_checkpoints(self.plan)
        mine.refresh_from_db()
        self.assertEqual(mine.status, 'pending',
                         "the plan must not retire a teacher's own choice")


class BehindTests(NightlyTestBase):

    def test_a_microbadge_long_past_its_target_is_flagged(self):
        late = self.badges[0]
        late.target_date = self.today - timedelta(days=constants.BEHIND_FLAG_DAYS + 1)
        late.save(update_fields=['target_date'])
        flagged = nightly.flag_if_behind(self.plan, self.today)
        self.goal.refresh_from_db()
        self.assertEqual(flagged, [self.goal])
        self.assertTrue(self.goal.needs_teacher_attention)
        self.assertIn('MicroBadge 1', self.goal.attention_reason)

    def test_a_little_late_is_left_alone(self):
        late = self.badges[0]
        late.target_date = self.today - timedelta(days=3)
        late.save(update_fields=['target_date'])
        self.assertEqual(nightly.flag_if_behind(self.plan, self.today), [])

    def test_nothing_is_moved(self):
        item = self.add_item(self.badges[0])
        late = self.badges[0]
        late.target_date = self.today - timedelta(days=30)
        late.save(update_fields=['target_date'])
        nightly.flag_if_behind(self.plan, self.today)
        item.refresh_from_db()
        self.assertEqual(item.micro_badge_id, late.id)


class WholeRunTests(NightlyTestBase):

    def test_running_it_twice_changes_nothing_the_second_time(self):
        cp = self.checkpoint(status='ready')
        self.add_item(self.badges[0], status='done')
        self.sit(cp, 9)

        nightly.run_for_plan(self.plan, self.today)
        snapshot = sorted(
            StudyPlanItem.objects.filter(plan=self.plan)
            .values_list('id', 'status', 'micro_badge_id'))
        badge_snapshot = sorted(
            StudyPlanMicroBadge.objects.filter(goal__plan=self.plan)
            .values_list('id', 'earned_at'))
        checkpoint_snapshot = sorted(
            StudyPlanCheckpoint.objects.filter(goal__plan=self.plan)
            .values_list('id', 'status', 'score'))

        second = nightly.run_for_plan(self.plan, self.today)
        self.assertEqual(
            sorted(StudyPlanItem.objects.filter(plan=self.plan)
                   .values_list('id', 'status', 'micro_badge_id')), snapshot)
        self.assertEqual(
            sorted(StudyPlanMicroBadge.objects.filter(goal__plan=self.plan)
                   .values_list('id', 'earned_at')), badge_snapshot)
        self.assertEqual(
            sorted(StudyPlanCheckpoint.objects.filter(goal__plan=self.plan)
                   .values_list('id', 'status', 'score')), checkpoint_snapshot)
        self.assertEqual((second['graded'], second['earned']), (0, 0))

    def test_a_locked_plan_is_left_alone(self):
        self.plan.is_locked = True
        self.plan.save(update_fields=['is_locked'])
        self.add_item(self.badges[0], status='done')
        nightly.run_for_plan(self.plan, self.today)
        self.badges[0].refresh_from_db()
        self.assertIsNone(self.badges[0].earned_at)

    def test_a_draft_plan_is_left_alone(self):
        self.plan.status = 'draft'
        self.plan.save(update_fields=['status'])
        self.add_item(self.badges[0], status='done')
        nightly.run_for_plan(self.plan, self.today)
        self.badges[0].refresh_from_db()
        self.assertIsNone(self.badges[0].earned_at)

    def test_the_plan_closes_once_every_topic_is_mastered(self):
        cp = self.checkpoint(status='ready')
        self.sit(cp, 10)
        nightly.run_for_plan(self.plan, self.today)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, 'completed')


class CommandTests(NightlyTestBase):

    def test_dry_run_writes_nothing(self):
        cp = self.checkpoint(status='ready')
        self.add_item(self.badges[0], status='done')
        self.sit(cp, 9)

        out = StringIO()
        call_command('run_study_plans', '--dry-run', stdout=out)

        cp.refresh_from_db()
        self.badges[0].refresh_from_db()
        self.plan.refresh_from_db()
        self.assertEqual(cp.status, 'ready')
        self.assertIsNone(self.badges[0].earned_at)
        self.assertIsNone(self.plan.last_checked_at)
        self.assertIn('nothing will be written', out.getvalue())

    def test_it_awards_and_marks_when_run_for_real(self):
        cp = self.checkpoint(status='ready')
        self.add_item(self.badges[0], status='done')
        self.sit(cp, 9)

        out = StringIO()
        call_command('run_study_plans', stdout=out)
        cp.refresh_from_db()
        self.badges[0].refresh_from_db()
        self.assertEqual(cp.status, 'passed')
        self.assertIsNotNone(self.badges[0].earned_at)
        self.assertIn('1 MicroBadge(s) earned', out.getvalue())

    def test_it_can_be_limited_to_one_student(self):
        other = User.objects.create_user('brian', password='pw')
        other_plan = StudyPlan.objects.create(
            student=other, teacher=self.teacher, subject=self.maths,
            title='Other', start_date=self.today,
            deadline=self.today + timedelta(days=14), status='active')

        out = StringIO()
        call_command('run_study_plans', '--student', 'brian', stdout=out)
        self.assertIn('1 active plan', out.getvalue())
