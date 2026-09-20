"""Building a plan: how the weeks fall, what gets chosen, and what is held back.

The rule worth guarding is the reservation: a part kept for a checkpoint must
never also be handed out as practice, or the capstone tests work the student has
already done with the marking scheme available.
"""
from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase

from core.models import Subject
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart
from homework.models import TeacherProfile
from interactive_lessons.models import Question, QuestionPart, Section, Topic
from studyplans import constants
from studyplans.models import (
    StudyPlan, StudyPlanCheckpointPart, StudyPlanGoal, StudyPlanItem, StudyPlanWeek,
)
from studyplans.services import planner


def make_teacher(username):
    user = User.objects.create_user(username=username, password='pw', is_staff=True)
    group, _ = Group.objects.get_or_create(name='Teachers')
    user.groups.add(group)
    profile, _ = TeacherProfile.objects.get_or_create(user=user)
    return user, profile


class PlannerTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(
            name='Differential Calculus', subject=cls.maths, paper='p1')
        cls.teacher_user, cls.teacher = make_teacher('ms_teacher')
        cls.student = User.objects.create_user('aoife', password='pw')

        # Plenty of exam parts: enough for a checkpoint, its retries, and practice.
        cls.parts = []
        for year in (2018, 2019, 2020, 2021):
            paper = ExamPaper.objects.create(
                subject=cls.maths, year=year, paper_type='p1',
                total_marks=300, is_published=True)
            question = ExamQuestion.objects.create(
                exam_paper=paper, question_number=6,
                topic=cls.topic, total_marks=30)
            for n, label in enumerate(['(a)', '(b)', '(c)'], start=1):
                cls.parts.append(ExamQuestionPart.objects.create(
                    question=question, label=label, max_marks=10,
                    order=n, topic=cls.topic))

        cls.sections = []
        for n in range(3):
            section = Section.objects.create(
                name=f'Section {n}', topic=cls.topic, order=n)
            for q in range(3):
                question = Question.objects.create(
                    topic=cls.topic, section=section, order=q)
                QuestionPart.objects.create(
                    question=question, label='(a)', prompt='p', answer='1',
                    max_marks=5, order=1)
            cls.sections.append(section)

    def spec(self, **overrides):
        spec = {'topic': self.topic, 'target_mastery': 75, 'priority': 1,
                'checkpoint_size': 2}
        spec.update(overrides)
        return spec


class WeekShapeTests(PlannerTestBase):

    def test_weeks_run_monday_to_sunday(self):
        # 2026-09-23 is a Wednesday.
        weeks = planner.build_weeks(date(2026, 9, 23), date(2026, 10, 11), 120)
        self.assertEqual(weeks[0].start_date, date(2026, 9, 21))  # Monday
        self.assertEqual(weeks[0].end_date, date(2026, 9, 27))    # Sunday
        for week in weeks:
            self.assertEqual(week.start_date.weekday(), 0)
            self.assertEqual(week.end_date.weekday(), 6)

    def test_a_partial_first_week_gets_a_smaller_budget(self):
        weeks = planner.build_weeks(date(2026, 9, 25), date(2026, 10, 11), 140)
        self.assertLess(weeks[0].minutes_budget, weeks[1].minutes_budget)
        self.assertEqual(weeks[1].minutes_budget, 140)

    def test_a_full_first_week_gets_the_whole_budget(self):
        weeks = planner.build_weeks(date(2026, 9, 21), date(2026, 10, 4), 140)
        self.assertEqual(weeks[0].minutes_budget, 140)

    def test_later_weeks_hold_some_time_back_for_the_nightly_run(self):
        weeks = planner.build_weeks(date(2026, 9, 21), date(2026, 10, 4), 100)
        self.assertLess(planner.spendable(weeks[1]), weeks[1].minutes_budget)


class ProposalTests(PlannerTestBase):

    def test_building_a_plan_writes_nothing_to_the_database(self):
        before = (StudyPlan.objects.count(), StudyPlanItem.objects.count(),
                  StudyPlanCheckpointPart.objects.count())
        planner.build_plan(
            self.student, [self.spec()],
            date(2026, 9, 21), date(2026, 10, 18), 120)
        after = (StudyPlan.objects.count(), StudyPlanItem.objects.count(),
                 StudyPlanCheckpointPart.objects.count())
        self.assertEqual(before, after)

    def test_it_reserves_a_checkpoint_and_parts_for_the_retries(self):
        proposal = planner.build_plan(
            self.student, [self.spec(checkpoint_size=2)],
            date(2026, 9, 21), date(2026, 10, 18), 120)
        goal = proposal.goals[0]
        self.assertEqual(len(goal.checkpoint_parts), 2)
        self.assertEqual(len(goal.reserve_rounds), constants.RETRY_ROUNDS)
        for round_parts in goal.reserve_rounds:
            self.assertEqual(len(round_parts), 2)

    def test_reserved_parts_are_never_handed_out_as_practice(self):
        """The capstone must test work the student has not already done."""
        proposal = planner.build_plan(
            self.student, [self.spec(checkpoint_size=2)],
            date(2026, 9, 21), date(2026, 11, 1), 240)
        reserved = proposal.goals[0].reserved_part_ids
        self.assertTrue(reserved)

        issued = {item.obj.id for week in proposal.weeks for item in week.items
                  if item.kind == 'exam_part'}
        self.assertFalse(reserved & issued,
                         "a reserved checkpoint part was issued as practice")

    def test_a_topic_with_no_exam_parts_is_a_warning_not_a_crash(self):
        bare = Topic.objects.create(name='Bare', subject=self.maths, paper='p1')
        proposal = planner.build_plan(
            self.student, [self.spec(topic=bare)],
            date(2026, 9, 21), date(2026, 10, 4), 120)
        self.assertEqual(proposal.goals[0].checkpoint_parts, [])
        self.assertTrue(any('cannot have a checkpoint' in w
                            for w in proposal.warnings))

    def test_a_thin_topic_warns_that_the_retries_will_run_out(self):
        thin = Topic.objects.create(name='Thin', subject=self.maths, paper='p1')
        paper = ExamPaper.objects.create(
            subject=self.maths, year=2017, paper_type='p1',
            total_marks=300, is_published=True)
        question = ExamQuestion.objects.create(
            exam_paper=paper, question_number=1, topic=thin, total_marks=20)
        for n, label in enumerate(['(a)', '(b)'], start=1):
            ExamQuestionPart.objects.create(
                question=question, label=label, max_marks=10, order=n, topic=thin)

        proposal = planner.build_plan(
            self.student, [self.spec(topic=thin, checkpoint_size=2)],
            date(2026, 9, 21), date(2026, 10, 4), 120)
        self.assertTrue(any('retries' in w for w in proposal.warnings))

    def test_a_deadline_before_the_start_is_refused(self):
        proposal = planner.build_plan(
            self.student, [self.spec()], date(2026, 10, 1), date(2026, 9, 1), 120)
        self.assertEqual(proposal.weeks, [])
        self.assertTrue(proposal.warnings)

    def test_no_week_is_given_more_items_than_the_cap(self):
        proposal = planner.build_plan(
            self.student, [self.spec()],
            date(2026, 9, 21), date(2026, 10, 18), 1200)
        for week in proposal.weeks:
            self.assertLessEqual(len(week.items), constants.MAX_ITEMS_PER_WEEK)

    def test_no_unit_is_handed_out_twice_in_one_plan(self):
        proposal = planner.build_plan(
            self.student, [self.spec()],
            date(2026, 9, 21), date(2026, 11, 15), 300)
        seen = set()
        for week in proposal.weeks:
            for item in week.items:
                key = (item.kind, item.obj.id)
                self.assertNotIn(key, seen, f"{key} was scheduled twice")
                seen.add(key)


class PersistTests(PlannerTestBase):

    def make_plan(self):
        return StudyPlan.objects.create(
            student=self.student, teacher=self.teacher, subject=self.maths,
            title='Autumn', start_date=date(2026, 9, 21),
            deadline=date(2026, 10, 18), status='active')

    def test_it_writes_goals_weeks_items_and_checkpoints(self):
        proposal = planner.build_plan(
            self.student, [self.spec(checkpoint_size=2)],
            date(2026, 9, 21), date(2026, 10, 18), 120)
        plan = self.make_plan()
        planner.persist_plan(plan, proposal)

        self.assertEqual(plan.goals.count(), 1)
        self.assertEqual(plan.weeks.count(), len(proposal.weeks))
        self.assertEqual(plan.items.count(), proposal.total_items)

        goal = plan.goals.first()
        # Round one plus a locked round for each retry held back.
        self.assertEqual(goal.checkpoints.count(), 1 + constants.RETRY_ROUNDS)
        self.assertEqual(goal.checkpoints.get(round=1).status, 'locked')

    def test_persisted_items_carry_their_week_dates(self):
        proposal = planner.build_plan(
            self.student, [self.spec()],
            date(2026, 9, 21), date(2026, 10, 4), 120)
        plan = self.make_plan()
        planner.persist_plan(plan, proposal)
        for item in plan.items.select_related('week'):
            self.assertEqual(item.available_from, item.week.start_date)
            self.assertEqual(item.due_date, item.week.end_date)

    def test_every_persisted_item_has_a_usable_link_and_label(self):
        proposal = planner.build_plan(
            self.student, [self.spec()],
            date(2026, 9, 21), date(2026, 10, 4), 120)
        plan = self.make_plan()
        planner.persist_plan(plan, proposal)
        for item in plan.items.all():
            self.assertNotEqual(item.get_content_url(), '#', item.content_type)
            self.assertNotEqual(item.get_content_display(), 'Unknown task')


class UncompletableWorkTests(PlannerTestBase):
    """Work a student could never tick off should never be scheduled."""

    def test_an_already_watched_quickflick_with_no_question_is_not_scheduled(self):
        from quickkicks.models import QuickKick, QuickKickView

        kick = QuickKick.objects.create(
            topic=self.topic, title='Chain rule', content_type='geogebra',
            geogebra_code='abc', order=1)
        QuickKickView.objects.create(user=self.student, quickkick=kick)

        candidates = planner.candidates_for_goal(self.student, self.topic, set())
        scheduled = [c for c in candidates
                     if c.kind == 'quickkick' and c.obj.id == kick.id]
        self.assertEqual(scheduled, [],
                         "a watched, question-less QuickFlick can never be completed")

    def test_an_already_watched_quickflick_with_a_question_is_still_offered(self):
        from quickkicks.models import QuickKick, QuickKickView

        kick = QuickKick.objects.create(
            topic=self.topic, title='Product rule', content_type='geogebra',
            geogebra_code='abc', order=2,
            question=Question.objects.filter(topic=self.topic).first())
        QuickKickView.objects.create(user=self.student, quickkick=kick)

        candidates = planner.candidates_for_goal(self.student, self.topic, set())
        scheduled = [c for c in candidates
                     if c.kind == 'quickkick' and c.obj.id == kick.id]
        self.assertEqual(len(scheduled), 1,
                         "its question can still be answered")

    def test_a_fully_completed_section_is_not_scheduled_again(self):
        from students.models import QuestionAttempt

        section = self.sections[0]
        for question in section.questions.all():
            QuestionAttempt.objects.create(
                student=self.student.studentprofile, question=question,
                question_part=question.parts.first(), student_answer='x',
                score_awarded=100, is_correct=True)

        candidates = planner.candidates_for_goal(self.student, self.topic, set())
        scheduled = [c for c in candidates
                     if c.kind == 'section' and c.obj.id == section.id]
        self.assertEqual(scheduled, [])


class WindowStartTests(PlannerTestBase):
    """Week one begins on a Monday that can predate the plan. The completion
    window must not."""

    def test_first_week_items_are_not_available_before_the_plan_starts(self):
        # A Thursday start: week one's Monday is three days earlier.
        start = date(2026, 9, 24)
        proposal = planner.build_plan(
            self.student, [self.spec()], start, date(2026, 10, 18), 120)
        plan = StudyPlan.objects.create(
            student=self.student, teacher=self.teacher, subject=self.maths,
            title='Thursday start', start_date=start,
            deadline=date(2026, 10, 18), status='active')
        planner.persist_plan(plan, proposal)

        first_week = plan.weeks.get(index=1)
        self.assertLess(first_week.start_date, start,
                        "this test is pointless unless week one predates the plan")
        for item in plan.items.filter(week=first_week):
            self.assertGreaterEqual(
                item.available_from, start,
                "an item was available before the plan began")

    def test_later_weeks_still_open_on_their_own_monday(self):
        start = date(2026, 9, 24)
        proposal = planner.build_plan(
            self.student, [self.spec()], start, date(2026, 10, 18), 120)
        plan = StudyPlan.objects.create(
            student=self.student, teacher=self.teacher, subject=self.maths,
            title='Thursday start 2', start_date=start,
            deadline=date(2026, 10, 18), status='active')
        planner.persist_plan(plan, proposal)
        for item in plan.items.exclude(week__index=1).select_related('week'):
            self.assertEqual(item.available_from, item.week.start_date)
