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
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart
from homework.models import TeacherClass, TeacherProfile
from interactive_lessons.models import Topic
from studyplans.models import (
    StudyPlan, StudyPlanCheckpoint, StudyPlanGoal, StudyPlanItem, StudyPlanWeek,
)
from studyplans.services import checkpoints as checkpoint_service


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
        self.client.force_login(self.teacher_user)
        response = self.client.post(
            reverse('studyplans:plan_create'),
            self.builder_post(student=str(self.classmate.id)))
        self.assertEqual(response.status_code, 302)
        plan = StudyPlan.objects.get(student=self.classmate, title='Spring plan')
        self.assertTrue(plan.goals.exists())
        self.assertTrue(plan.weeks.exists())

    def test_rolling_out_to_a_class_gives_every_student_their_own_plan(self):
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

    def test_the_student_dashboard_shows_the_plan_card(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['study_plan_card'])
        self.assertContains(response, self.plan.title)
