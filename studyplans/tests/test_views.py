"""Who can see and change a study plan, and what a mere page load is allowed to do.

The access rules matter because a plan carries a student's marks. The other rule
under test is that a GET never writes -- the pattern this app was built to avoid
repeating.
"""
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Subject
from exam_papers.models import (
    ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionAttempt, ExamQuestionPart,
)
from homework.models import TeacherClass, TeacherProfile
from interactive_lessons.models import Topic
from studyplans.models import (
    StudyPlan, StudyPlanCheckpoint, StudyPlanGoal, StudyPlanItem,
    StudyPlanMicroBadge, StudyPlanWeek,
)
from studyplans.services import checkpoints as checkpoint_service
from studyplans.services import nightly


def make_teacher(username):
    user = User.objects.create_user(username=username, password='pw', is_staff=True)
    group, _ = Group.objects.get_or_create(name='Teachers')
    user.groups.add(group)
    profile, _ = TeacherProfile.objects.get_or_create(user=user)
    return user, profile


def make_student(username):
    user = User.objects.create_user(username=username, password='pw')
    group, _ = Group.objects.get_or_create(name='Students')
    user.groups.add(group)
    return user


class ViewTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(
            name='Integration', subject=cls.maths, paper='p1')

        cls.teacher_user, cls.teacher = make_teacher('ms_teacher')
        cls.other_teacher_user, cls.other_teacher = make_teacher('mr_other')

        cls.student = make_student('aoife')
        cls.classmate = make_student('brian')
        cls.stranger = make_student('ciara')

        cls.klass = TeacherClass.objects.create(
            teacher=cls.teacher, name='6th Year Maths A')
        cls.klass.students.add(cls.student, cls.classmate)

        cls.parts = []
        for year in (2019, 2020, 2021, 2022, 2023, 2024):
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

        cls.today = timezone.localdate()
        cls.plan = StudyPlan.objects.create(
            student=cls.student, teacher=cls.teacher, subject=cls.maths,
            title='Christmas Push', start_date=cls.today,
            deadline=cls.today + timedelta(days=21), status='active',
            teacher_class=cls.klass)
        cls.goal = StudyPlanGoal.objects.create(
            plan=cls.plan, topic=cls.topic, checkpoint_size=2)
        cls.week = StudyPlanWeek.objects.create(
            plan=cls.plan, index=1, start_date=cls.today,
            end_date=cls.today + timedelta(days=6), minutes_budget=120)
        cls.item = StudyPlanItem.objects.create(
            plan=cls.plan, week=cls.week, goal=cls.goal,
            content_type='exam_part', exam_question_part=cls.parts[4],
            estimated_minutes=5, available_from=cls.today,
            due_date=cls.today + timedelta(days=6))

    def builder_post(self, **overrides):
        data = {
            'title': 'Spring plan',
            'start_date': self.today.isoformat(),
            'deadline': (self.today + timedelta(days=21)).isoformat(),
            'weekly_minutes': '120',
            'topics': [str(self.topic.id)],
            f'target_{self.topic.id}': '75',
            f'priority_{self.topic.id}': '1',
            f'size_{self.topic.id}': '2',
        }
        data.update(overrides)
        return data


class AccessTests(ViewTestBase):

    def test_a_student_cannot_open_another_students_plan(self):
        self.client.force_login(self.stranger)
        response = self.client.get(
            reverse('studyplans:plan_detail', args=[self.plan.id]))
        self.assertEqual(response.status_code, 403)

    def test_a_student_can_open_their_own_plan(self):
        self.client.force_login(self.student)
        response = self.client.get(
            reverse('studyplans:plan_detail', args=[self.plan.id]))
        self.assertEqual(response.status_code, 200)

    def test_a_teacher_from_another_class_cannot_open_the_plan(self):
        self.client.force_login(self.other_teacher_user)
        response = self.client.get(
            reverse('studyplans:plan_manage', args=[self.plan.id]))
        self.assertEqual(response.status_code, 403)

    def test_the_owning_teacher_can_open_it(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(
            reverse('studyplans:plan_manage', args=[self.plan.id]))
        self.assertEqual(response.status_code, 200)

    def test_a_student_cannot_reach_the_teacher_pages(self):
        self.client.force_login(self.student)
        for name, args in (('studyplans:teacher_dashboard', []),
                           ('studyplans:plan_builder', []),
                           ('studyplans:class_oversight', [self.klass.id])):
            response = self.client.get(reverse(name, args=args))
            self.assertEqual(response.status_code, 403, name)

    def test_a_teacher_cannot_see_another_teachers_class(self):
        self.client.force_login(self.other_teacher_user)
        response = self.client.get(
            reverse('studyplans:class_oversight', args=[self.klass.id]))
        self.assertEqual(response.status_code, 403)

    def test_a_student_cannot_tick_someone_elses_item(self):
        self.client.force_login(self.stranger)
        response = self.client.post(
            reverse('studyplans:toggle_item', args=[self.item.id]))
        self.assertEqual(response.status_code, 403)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'pending')


class ReadOnlyGetTests(ViewTestBase):

    def test_refreshing_progress_refuses_a_get(self):
        """A GET that writes is the bug this app exists partly to avoid."""
        self.client.force_login(self.student)
        response = self.client.get(
            reverse('studyplans:refresh_progress', args=[self.plan.id]))
        self.assertEqual(response.status_code, 405)

    def test_opening_the_plan_page_writes_nothing(self):
        self.client.force_login(self.student)
        before = list(StudyPlanItem.objects.filter(plan=self.plan)
                      .values_list('id', 'status', 'started_at'))
        checked_before = self.plan.last_checked_at

        self.client.get(reverse('studyplans:my_plan'))
        self.client.get(reverse('studyplans:plan_detail', args=[self.plan.id]))

        after = list(StudyPlanItem.objects.filter(plan=self.plan)
                     .values_list('id', 'status', 'started_at'))
        self.plan.refresh_from_db()
        self.assertEqual(before, after)
        self.assertEqual(self.plan.last_checked_at, checked_before)


class StudentPageTests(ViewTestBase):

    def test_my_plan_leads_with_topics_mastered(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('studyplans:my_plan'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'topic')
        self.assertEqual(response.context['card']['total'], 1)
        self.assertEqual(response.context['card']['mastered'], 0)

    def test_a_student_with_no_plan_gets_a_friendly_page(self):
        self.client.force_login(self.stranger)
        response = self.client.get(reverse('studyplans:my_plan'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['plan'])

    def test_starting_an_item_stamps_it_and_sends_them_to_the_work(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('studyplans:start_item', args=[self.item.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('practise', response.url)
        self.item.refresh_from_db()
        self.assertIsNotNone(self.item.started_at)


class AchievementsTests(ViewTestBase):

    def pass_a_checkpoint(self, plan, goal, score=88.0):
        checkpoint = StudyPlanCheckpoint.objects.create(
            goal=goal, round=1, status='passed', pass_mark=75,
            marks_awarded=17.6, marks_possible=20.0, score=score,
            sat_at=timezone.now())
        goal.mastered_at = checkpoint.sat_at
        goal.mastery_score = score
        goal.save(update_fields=['mastered_at', 'mastery_score'])
        return checkpoint

    def test_it_gathers_passes_from_every_plan_the_student_has_had(self):
        self.pass_a_checkpoint(self.plan, self.goal, 88.0)

        older_topic = Topic.objects.create(
            name='Complex Numbers', subject=self.maths, paper='p1')
        older = StudyPlan.objects.create(
            student=self.student, teacher=self.teacher, subject=self.maths,
            title='Hallowe\'en plan', start_date=self.today - timedelta(days=60),
            deadline=self.today - timedelta(days=30), status='archived')
        older_goal = StudyPlanGoal.objects.create(plan=older, topic=older_topic)
        self.pass_a_checkpoint(older, older_goal, 92.0)

        self.client.force_login(self.student)
        response = self.client.get(reverse('studyplans:achievements'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['achievements']['total'], 2)
        self.assertContains(response, 'Complex Numbers')
        self.assertContains(response, 'Integration')

    def test_it_shows_only_this_students_achievements(self):
        self.pass_a_checkpoint(self.plan, self.goal)

        other_plan = StudyPlan.objects.create(
            student=self.classmate, teacher=self.teacher, subject=self.maths,
            title='Brian', start_date=self.today,
            deadline=self.today + timedelta(days=14), status='active')
        other_goal = StudyPlanGoal.objects.create(
            plan=other_plan, topic=self.topic)
        self.pass_a_checkpoint(other_plan, other_goal)

        self.client.force_login(self.classmate)
        response = self.client.get(reverse('studyplans:achievements'))
        self.assertEqual(response.context['achievements']['total'], 1)

    def test_a_failed_checkpoint_is_not_an_achievement(self):
        StudyPlanCheckpoint.objects.create(
            goal=self.goal, round=1, status='failed', pass_mark=75,
            score=40.0, sat_at=timezone.now())
        self.client.force_login(self.student)
        response = self.client.get(reverse('studyplans:achievements'))
        self.assertEqual(response.context['achievements']['total'], 0)


class BuilderTests(ViewTestBase):

    def test_previewing_a_plan_writes_nothing(self):
        self.client.force_login(self.teacher_user)
        before = StudyPlan.objects.count(), StudyPlanItem.objects.count()
        response = self.client.post(
            reverse('studyplans:plan_preview'),
            self.builder_post(student=str(self.classmate.id)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            (StudyPlan.objects.count(), StudyPlanItem.objects.count()), before)

    def test_creating_a_plan_for_one_student(self):
        # brian holds no plan; aoife's fixture plan is irrelevant here.
        self.client.force_login(self.teacher_user)
        response = self.client.post(
            reverse('studyplans:plan_create'),
            self.builder_post(student=str(self.classmate.id)))
        self.assertEqual(response.status_code, 302)
        plan = StudyPlan.objects.get(student=self.classmate, title='Spring plan')
        self.assertTrue(plan.goals.exists())
        self.assertEqual(plan.goals.get().micro_badges.filter(kind='core').count(), 10)

    def test_rolling_out_to_a_class_gives_every_student_their_own_plan(self):
        # aoife already holds the fixture plan, and a student may have only one
        # active at a time, so free her slot before rolling out to the class.
        self.plan.archive()
        self.client.force_login(self.teacher_user)
        self.client.post(reverse('studyplans:plan_create'),
                         self.builder_post(teacher_class=str(self.klass.id)))
        made = StudyPlan.objects.filter(title='Spring plan')
        self.assertEqual(made.count(), self.klass.students.count())
        self.assertEqual(
            set(made.values_list('student__username', flat=True)),
            {'aoife', 'brian'})

    def test_rolling_out_twice_does_not_double_up(self):
        """A double-clicked rollout must not give everyone two plans."""
        self.plan.archive()
        self.client.force_login(self.teacher_user)
        payload = self.builder_post(teacher_class=str(self.klass.id))
        self.client.post(reverse('studyplans:plan_create'), payload)
        first = StudyPlan.objects.filter(title='Spring plan').count()
        self.assertEqual(first, self.klass.students.count())

        self.client.post(reverse('studyplans:plan_create'), payload)
        self.assertEqual(
            StudyPlan.objects.filter(title='Spring plan').count(), first,
            "the second rollout should have been skipped entirely")

    def test_a_teacher_cannot_build_for_a_student_they_do_not_teach(self):
        self.client.force_login(self.other_teacher_user)
        response = self.client.post(
            reverse('studyplans:plan_create'),
            self.builder_post(student=str(self.student.id)))
        self.assertEqual(response.status_code, 403)


class TeacherActionTests(ViewTestBase):

    def test_removing_an_item_keeps_the_row(self):
        self.client.force_login(self.teacher_user)
        self.client.post(reverse('studyplans:remove_item',
                                 args=[self.plan.id, self.item.id]))
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'skipped')
        self.assertTrue(StudyPlanItem.objects.filter(id=self.item.id).exists())

    def test_a_teacher_can_unlock_a_checkpoint_early(self):
        checkpoint = checkpoint_service.create_checkpoint(
            self.goal, parts=self.parts[:2], status='locked')
        self.client.force_login(self.teacher_user)
        self.client.post(
            reverse('studyplans:manage_checkpoint',
                    args=[self.plan.id, checkpoint.id]),
            {'action': 'unlock'})
        checkpoint.refresh_from_db()
        self.assertEqual(checkpoint.status, 'ready')
        self.assertIsNotNone(checkpoint.unlocked_at)

    def test_the_candidate_api_reports_what_a_topic_can_support(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(
            reverse('studyplans:topic_candidates', args=[self.topic.id]),
            {'size': 2})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['topic'], 'Integration')
        self.assertEqual(len(data['suggested']), 2)
        self.assertIn('sufficient', data)


class EveryPageRendersTests(ViewTestBase):
    """Cheap insurance: a template that does not render is invisible until
    someone opens the page, and these are pages a teacher opens rarely."""

    def test_the_builder_renders(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('studyplans:plan_builder'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Build a Study Plan')

    def test_the_checkpoint_page_renders_before_it_is_sat(self):
        checkpoint = checkpoint_service.create_checkpoint(
            self.goal, parts=self.parts[:2], status='ready')
        self.client.force_login(self.student)
        response = self.client.get(
            reverse('studyplans:checkpoint_detail', args=[checkpoint.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'to sit')

    def test_the_checkpoint_page_renders_after_it_is_sat(self):
        checkpoint = StudyPlanCheckpoint.objects.create(
            goal=self.goal, round=1, status='passed', pass_mark=75,
            marks_awarded=18.0, marks_possible=20.0, score=90.0,
            sat_at=timezone.now())
        self.client.force_login(self.student)
        response = self.client.get(
            reverse('studyplans:checkpoint_detail', args=[checkpoint.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'passed')

    def test_the_student_oversight_page_renders(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(
            reverse('studyplans:student_oversight', args=[self.student.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.username)

    def test_the_class_oversight_page_renders(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(
            reverse('studyplans:class_oversight', args=[self.klass.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.klass.name)

    def test_the_teacher_dashboard_renders(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('studyplans:teacher_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.plan.title)

    def test_an_archived_plan_is_listed_apart_on_the_dashboard(self):
        self.plan.status = 'archived'
        self.plan.save()
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('studyplans:teacher_dashboard'))
        self.assertEqual(response.context['rows'], [])
        self.assertEqual(list(response.context['archived']), [self.plan])
        self.assertContains(response, reverse('studyplans:plan_manage', args=[self.plan.id]))

    def test_another_teachers_archived_plan_is_not_listed(self):
        self.plan.status = 'archived'
        self.plan.save()
        self.client.force_login(self.other_teacher_user)
        response = self.client.get(reverse('studyplans:teacher_dashboard'))
        self.assertEqual(list(response.context['archived']), [])

    def test_the_student_dashboard_shows_the_plan_card(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['study_plan_card'])
        self.assertContains(response, self.plan.title)


class MarkingACheckpointTests(ViewTestBase):
    """A student who has answered every part must be able to see that, and get
    a result, without waiting for the nightly run."""

    def setUp(self):
        self.checkpoint = checkpoint_service.create_checkpoint(
            self.goal, parts=self.parts[:2], status='ready')

    def answer(self, part, marks):
        attempt, _ = ExamAttempt.objects.get_or_create(
            student=self.student, exam_paper=part.question.exam_paper,
            attempt_mode='question_practice')
        ExamQuestionAttempt.objects.create(
            exam_attempt=attempt, question_part=part, student_answer='x',
            marks_awarded=marks, max_marks=10)

    def page(self):
        return self.client.get(
            reverse('studyplans:checkpoint_detail', args=[self.checkpoint.id]))

    def test_answered_parts_are_acknowledged(self):
        self.answer(self.parts[0], 10)
        self.client.force_login(self.student)
        response = self.page()
        self.assertContains(response, 'answered', count=1)
        self.assertNotContains(response, 'Mark my Badge Test')

    def test_marking_is_offered_once_every_part_is_answered(self):
        self.answer(self.parts[0], 10)
        self.answer(self.parts[1], 9)
        self.client.force_login(self.student)
        self.assertContains(self.page(), 'Mark my Badge Test')
        self.checkpoint.refresh_from_db()
        self.assertEqual(self.checkpoint.status, 'ready')  # the GET wrote nothing

    def test_marking_it_gives_a_result(self):
        self.answer(self.parts[0], 10)
        self.answer(self.parts[1], 9)
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('studyplans:mark_checkpoint', args=[self.checkpoint.id]))
        self.assertRedirects(response, reverse(
            'studyplans:checkpoint_detail', args=[self.checkpoint.id]))
        self.checkpoint.refresh_from_db()
        self.assertEqual(self.checkpoint.status, 'passed')
        self.assertEqual(self.checkpoint.score, 95)

    def test_marking_an_unfinished_checkpoint_leaves_it_open(self):
        self.answer(self.parts[0], 10)
        self.client.force_login(self.student)
        self.client.post(
            reverse('studyplans:mark_checkpoint', args=[self.checkpoint.id]))
        self.checkpoint.refresh_from_db()
        self.assertEqual(self.checkpoint.status, 'ready')

    def test_another_student_cannot_mark_it(self):
        self.answer(self.parts[0], 10)
        self.answer(self.parts[1], 9)
        self.client.force_login(self.stranger)
        response = self.client.post(
            reverse('studyplans:mark_checkpoint', args=[self.checkpoint.id]))
        self.assertEqual(response.status_code, 403)
        self.checkpoint.refresh_from_db()
        self.assertEqual(self.checkpoint.status, 'ready')

    def test_stale_progress_is_checked_on_arrival(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('studyplans:my_plan'))
        self.assertContains(response, 'id="refresh-progress"')
        self.assertContains(response, "fetch(form.action")


class MicroBadgeEditingTests(ViewTestBase):
    """The teacher shapes each MicroBadge after the planner has filled it."""

    def setUp(self):
        self.badges = [
            StudyPlanMicroBadge.objects.create(
                goal=self.goal, number=n,
                target_date=self.today + timedelta(days=2 * n))
            for n in range(1, 11)
        ]
        self.item.micro_badge = self.badges[0]
        self.item.save()

    def test_moving_an_item_to_another_microbadge(self):
        self.client.force_login(self.teacher_user)
        self.client.post(
            reverse('studyplans:move_item', args=[self.plan.id, self.item.id]),
            {'micro_badge': self.badges[4].id})
        self.item.refresh_from_db()
        self.assertEqual(self.item.micro_badge, self.badges[4])
        self.assertEqual(self.item.due_date, self.badges[4].target_date)

    def _second_item(self, order):
        """Another item in MicroBadge 1, sharing the first's order if asked."""
        return StudyPlanItem.objects.create(
            plan=self.plan, goal=self.goal, micro_badge=self.badges[0],
            content_type='exam_part', exam_question_part=self.parts[5],
            order=order, available_from=self.item.available_from,
            due_date=self.item.due_date)

    def _order(self):
        return list(self.badges[0].items.order_by('order', 'id')
                    .values_list('id', flat=True))

    def test_moving_an_item_up_within_its_microbadge(self):
        second = self._second_item(order=self.item.order + 1)
        self.client.force_login(self.teacher_user)
        response = self.client.post(
            reverse('studyplans:reorder_item', args=[self.plan.id, second.id]),
            {'direction': 'up'})
        self.assertEqual(self._order(), [second.id, self.item.id])
        self.assertTrue(response.url.endswith(f'#badge-{self.badges[0].id}'))

    def test_reordering_works_when_orders_tie(self):
        second = self._second_item(order=self.item.order)
        self.client.force_login(self.teacher_user)
        self.client.post(
            reverse('studyplans:reorder_item', args=[self.plan.id, self.item.id]),
            {'direction': 'down'})
        self.assertEqual(self._order(), [second.id, self.item.id])

    def test_the_top_item_cannot_move_further_up(self):
        second = self._second_item(order=self.item.order + 1)
        self.client.force_login(self.teacher_user)
        self.client.post(
            reverse('studyplans:reorder_item', args=[self.plan.id, self.item.id]),
            {'direction': 'up'})
        self.assertEqual(self._order(), [self.item.id, second.id])

    def test_another_teacher_cannot_reorder(self):
        self.client.force_login(self.other_teacher_user)
        response = self.client.post(
            reverse('studyplans:reorder_item', args=[self.plan.id, self.item.id]),
            {'direction': 'down'})
        self.assertEqual(response.status_code, 403)

    def test_an_item_cannot_move_to_another_topics_microbadge(self):
        other_topic = Topic.objects.create(name='Other', subject=self.maths, paper='p1')
        other_goal = StudyPlanGoal.objects.create(plan=self.plan, topic=other_topic)
        foreign = StudyPlanMicroBadge.objects.create(
            goal=other_goal, number=1, target_date=self.today)
        self.client.force_login(self.teacher_user)
        response = self.client.post(
            reverse('studyplans:move_item', args=[self.plan.id, self.item.id]),
            {'micro_badge': foreign.id})
        self.assertEqual(response.status_code, 404)

    def test_adding_unused_practice_to_a_microbadge(self):
        part = self.parts[5]
        self.client.force_login(self.teacher_user)
        self.client.post(
            reverse('studyplans:add_item', args=[self.plan.id, self.badges[2].id]),
            {'content': f'exam_part:{part.id}'})
        added = self.badges[2].items.get()
        self.assertEqual((added.exam_question_part, added.origin), (part, 'teacher'))

    def test_something_already_on_the_plan_cannot_be_added_again(self):
        self.client.force_login(self.teacher_user)
        self.client.post(
            reverse('studyplans:add_item', args=[self.plan.id, self.badges[2].id]),
            {'content': f'exam_part:{self.item.exam_question_part_id}'})
        self.assertFalse(self.badges[2].items.exists())

    def test_awarding_a_microbadge_by_hand(self):
        self.client.force_login(self.teacher_user)
        self.client.post(
            reverse('studyplans:award_microbadge', args=[self.plan.id, self.badges[9].id]))
        self.badges[9].refresh_from_db()
        self.assertTrue(self.badges[9].is_earned)
        self.assertTrue(self.badges[9].earned_by_teacher)

    def test_a_student_cannot_award_their_own(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('studyplans:award_microbadge', args=[self.plan.id, self.badges[9].id]))
        self.assertEqual(response.status_code, 403)
        self.badges[9].refresh_from_db()
        self.assertFalse(self.badges[9].is_earned)

    def test_another_teacher_cannot_edit(self):
        self.client.force_login(self.other_teacher_user)
        response = self.client.post(
            reverse('studyplans:move_item', args=[self.plan.id, self.item.id]),
            {'micro_badge': self.badges[4].id})
        self.assertEqual(response.status_code, 403)

    def test_ticking_the_last_item_earns_the_microbadge(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('studyplans:toggle_item', args=[self.item.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.json()['earned'], 1)
        self.badges[0].refresh_from_db()
        self.assertTrue(self.badges[0].is_earned)

    def test_the_pages_render_with_microbadges(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('studyplans:plan_manage', args=[self.plan.id]))
        self.assertContains(response, 'MicroBadge 10')
        self.client.force_login(self.student)
        for name in ('studyplans:my_plan',):
            response = self.client.get(reverse(name))
            self.assertContains(response, 'Next: MicroBadge 1')
        response = self.client.get(reverse('studyplans:plan_detail', args=[self.plan.id]))
        self.assertContains(response, 'MicroBadge 10')


class DraftPlanTests(ViewTestBase):
    """A draft is shaped by the teacher before the student ever sees it."""

    def post(self, **extra):
        self.client.force_login(self.teacher_user)
        data = self.builder_post(student=str(self.classmate.id))
        data.update(extra)
        return self.client.post(reverse('studyplans:plan_create'), data)

    def test_saving_as_a_draft_keeps_it_from_the_student(self):
        self.post(save='draft')
        plan = StudyPlan.objects.get(student=self.classmate, title='Spring plan')
        self.assertEqual(plan.status, 'draft')
        self.assertEqual(plan.goals.get().micro_badges.count(), 10)

        self.client.force_login(self.classmate)
        response = self.client.get(reverse('studyplans:my_plan'))
        self.assertIsNone(response.context['plan'])

    def test_a_blank_draft_has_its_microbadges_but_no_work(self):
        """A draft plan is expected to generate work; this tells a blank one apart."""
        self.post(save='draft')
        self.assertTrue(StudyPlan.objects.get(
            student=self.classmate, title='Spring plan').items.exists())

        StudyPlan.objects.filter(student=self.classmate).delete()
        self.post(save='blank')
        plan = StudyPlan.objects.get(student=self.classmate, title='Spring plan')
        self.assertEqual(plan.status, 'draft')
        self.assertEqual(plan.goals.get().micro_badges.count(), 10)
        self.assertFalse(plan.items.exists())

    def test_the_preview_offers_a_blank_draft(self):
        self.client.force_login(self.teacher_user)
        response = self.client.post(
            reverse('studyplans:plan_preview'),
            self.builder_post(student=str(self.classmate.id)))
        self.assertContains(response, 'value="blank"')

    def test_a_draft_does_not_need_the_active_slot(self):
        """aoife already holds the fixture plan; a draft must still be allowed."""
        self.client.force_login(self.teacher_user)
        data = self.builder_post(student=str(self.student.id))
        data['save'] = 'draft'
        self.client.post(reverse('studyplans:plan_create'), data)
        self.assertTrue(StudyPlan.objects.filter(
            student=self.student, title='Spring plan', status='draft').exists())
        self.assertEqual(StudyPlan.objects.filter(
            student=self.student, status='active').count(), 1)

    def test_without_the_draft_button_it_goes_live(self):
        self.post()
        plan = StudyPlan.objects.get(student=self.classmate, title='Spring plan')
        self.assertEqual(plan.status, 'active')

    def test_a_draft_can_be_handed_over_later(self):
        self.post(save='draft')
        plan = StudyPlan.objects.get(student=self.classmate, title='Spring plan')
        self.client.post(reverse('studyplans:set_plan_status', args=[plan.id]),
                         {'action': 'activate'})
        plan.refresh_from_db()
        self.assertEqual(plan.status, 'active')

    def test_the_preview_offers_the_draft_button(self):
        self.client.force_login(self.teacher_user)
        response = self.client.post(reverse('studyplans:plan_preview'),
                                    self.builder_post(student=str(self.classmate.id)))
        self.assertContains(response, 'Save as draft')


class AddingWorkBackTests(ViewTestBase):
    """Removing an item must not put it out of reach for good."""

    def setUp(self):
        self.badge = StudyPlanMicroBadge.objects.create(
            goal=self.goal, number=1, target_date=self.today + timedelta(days=3))
        self.item.micro_badge = self.badge
        self.item.save()
        self.client.force_login(self.teacher_user)

    def add(self, part):
        return self.client.post(
            reverse('studyplans:add_item', args=[self.plan.id, self.badge.id]),
            {'content': f'exam_part:{part.id}'})

    def test_a_removed_item_can_be_added_back(self):
        self.client.post(
            reverse('studyplans:remove_item', args=[self.plan.id, self.item.id]))
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'skipped')

        self.add(self.item.exam_question_part)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'pending')
        self.assertEqual(self.item.micro_badge, self.badge)
        self.assertEqual(self.item.origin, 'teacher')

    def test_adding_it_back_does_not_make_a_second_row(self):
        part = self.item.exam_question_part
        self.client.post(
            reverse('studyplans:remove_item', args=[self.plan.id, self.item.id]))
        self.add(part)
        self.assertEqual(
            self.plan.items.filter(exam_question_part=part).count(), 1)

    def test_the_nightly_run_never_revives_what_a_teacher_removed(self):
        self.client.post(
            reverse('studyplans:remove_item', args=[self.plan.id, self.item.id]))
        offered = [(c.kind, c.obj.id)
                   for c in nightly.revisit_candidates(self.plan, self.goal)]
        self.assertNotIn(('exam_part', self.item.exam_question_part_id), offered)

    def test_the_teachers_own_list_offers_it_back(self):
        self.client.post(
            reverse('studyplans:remove_item', args=[self.plan.id, self.item.id]))
        offered = [(c.kind, c.obj.id) for c in nightly.revisit_candidates(
            self.plan, self.goal, allow_removed=True)]
        self.assertIn(('exam_part', self.item.exam_question_part_id), offered)

    def test_a_topic_with_nothing_left_says_so(self):
        for part in self.parts:
            StudyPlanItem.objects.create(
                plan=self.plan, goal=self.goal, micro_badge=self.badge,
                content_type='exam_part', exam_question_part=part,
                estimated_minutes=5, available_from=self.today,
                due_date=self.today + timedelta(days=3))
        response = self.client.get(
            reverse('studyplans:plan_manage', args=[self.plan.id]))
        self.assertContains(response, 'Nothing left on this topic to add')
