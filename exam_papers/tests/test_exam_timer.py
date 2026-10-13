"""Leaving a timed exam without pausing stops the clock rather than running it out."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Subject
from exam_papers.models import (ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionAttempt,
                                ExamQuestionPart)


class TimedExamSetup:
    def setUp(self):
        maths, _ = Subject.objects.get_or_create(slug='maths', defaults={'name': 'Maths'})
        self.paper = ExamPaper.objects.create(subject=maths, year=2018, paper_type='p1',
                                              total_marks=300, is_published=True,
                                              time_limit_minutes=150)
        self.question = ExamQuestion.objects.create(exam_paper=self.paper, question_number=1,
                                                    total_marks=25)
        ExamQuestionPart.objects.create(question=self.question, label='(a)', max_marks=10, order=1)
        self.student = User.objects.create_user('aoife', password='pw')
        self.client.force_login(self.student)
        self.attempt = ExamAttempt.objects.create(student=self.student, exam_paper=self.paper,
                                                  attempt_mode='full_timed')
        self.url = reverse('exam_papers:question_interface',
                           args=[self.attempt.id, self.question.id])

    def rewind(self, started_minutes_ago, last_seen_minutes_ago=None):
        """Pretend the attempt began, and the page last checked in, a while ago."""
        now = timezone.now()
        ExamAttempt.objects.filter(id=self.attempt.id).update(
            started_at=now - timedelta(minutes=started_minutes_ago),
            last_seen_at=(None if last_seen_minutes_ago is None
                          else now - timedelta(minutes=last_seen_minutes_ago)))
        self.attempt.refresh_from_db()


class ExamTimerTests(TimedExamSetup, TestCase):
    def test_coming_back_days_later_resumes_with_the_time_that_was_left(self):
        # 20 minutes in, then the laptop was shut for three days
        self.rewind(started_minutes_ago=3 * 24 * 60 + 20, last_seen_minutes_ago=3 * 24 * 60)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertAlmostEqual(response.context['time_remaining'], 130 * 60, delta=5)
        self.attempt.refresh_from_db()
        self.assertFalse(self.attempt.is_completed)

    def test_the_clock_keeps_running_while_the_page_is_open(self):
        # Checked in a minute ago, which is within the grace period
        self.rewind(started_minutes_ago=60, last_seen_minutes_ago=1)

        response = self.client.post(reverse('exam_papers:exam_heartbeat', args=[self.attempt.id]))

        self.assertAlmostEqual(response.json()['time_remaining'], 90 * 60, delta=5)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.total_paused_seconds, 0)

    def test_running_out_of_time_with_the_page_open_still_submits(self):
        self.rewind(started_minutes_ago=151, last_seen_minutes_ago=0)

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse('exam_papers:view_results', args=[self.attempt.id]))
        self.attempt.refresh_from_db()
        self.assertTrue(self.attempt.is_completed)

    def test_a_pause_is_not_counted_twice_after_resuming(self):
        self.rewind(started_minutes_ago=60, last_seen_minutes_ago=0)
        self.client.post(reverse('exam_papers:pause_exam', args=[self.attempt.id]))
        # Paused for 30 minutes, page closed the whole time
        ExamAttempt.objects.filter(id=self.attempt.id).update(
            paused_at=timezone.now() - timedelta(minutes=30),
            last_seen_at=timezone.now() - timedelta(minutes=30))

        self.client.post(reverse('exam_papers:resume_exam', args=[self.attempt.id]))
        response = self.client.get(self.url)

        # 60 minutes on the clock less the 30 paused leaves 120 of 150
        self.assertAlmostEqual(response.context['time_remaining'], 120 * 60, delta=5)

    def test_the_paper_list_says_times_up_rather_than_offering_resume(self):
        # Started before presence was tracked and never paused: the time is gone
        self.rewind(started_minutes_ago=7 * 24 * 60)

        response = self.client.get(reverse('exam_papers:paper_list'))

        self.assertContains(response, "Time's up")
        self.assertContains(response, 'See Results')
        self.assertNotContains(response, 'Resume Exam')

    def test_the_paper_list_offers_resume_after_leaving_without_pausing(self):
        self.rewind(started_minutes_ago=7 * 24 * 60 + 10, last_seen_minutes_ago=7 * 24 * 60)

        response = self.client.get(reverse('exam_papers:paper_list'))

        self.assertContains(response, 'Resume Exam')
        self.assertNotContains(response, "Time's up")


class StartOverTests(TimedExamSetup, TestCase):
    """Start over abandons an unfinished timed attempt without losing its answers."""

    def restart(self, attempt=None):
        return self.client.post(
            reverse('exam_papers:restart_exam', args=[(attempt or self.attempt).id]))

    def answer(self, marks):
        part = self.question.parts.get()
        ExamQuestionAttempt.objects.create(
            exam_attempt=self.attempt, question_part=part, student_answer='4',
            marks_awarded=marks, max_marks=10, is_correct=marks == 10)

    def test_starting_over_gives_a_fresh_attempt_with_the_full_time(self):
        self.rewind(started_minutes_ago=100, last_seen_minutes_ago=0)

        response = self.restart()

        fresh = ExamAttempt.objects.exclude(id=self.attempt.id).get()
        self.assertRedirects(response, reverse('exam_papers:question_interface',
                                               args=[fresh.id, self.question.id]))
        self.assertEqual(fresh.attempt_mode, 'full_timed')
        self.assertAlmostEqual(fresh.time_remaining_seconds(), 150 * 60, delta=5)

    def test_the_old_attempt_is_closed_but_its_answers_are_kept(self):
        self.answer(10)

        self.restart()

        self.attempt.refresh_from_db()
        self.assertTrue(self.attempt.is_completed)
        self.assertIsNotNone(self.attempt.started_over_at)
        # Homework, plans and reports count these answers
        self.assertEqual(self.attempt.question_attempts.count(), 1)

    def test_a_paused_attempt_can_be_started_over(self):
        self.client.post(reverse('exam_papers:pause_exam', args=[self.attempt.id]))

        self.restart()

        self.attempt.refresh_from_db()
        self.assertTrue(self.attempt.is_completed)
        self.assertFalse(self.attempt.is_paused)

    def test_the_best_score_badge_ignores_an_attempt_given_up_on(self):
        # One right answer out of one tried would show as 100%
        self.answer(10)
        self.restart()

        response = self.client.get(reverse('exam_papers:paper_list'))

        self.assertNotContains(response, '✓ 100%')

    def test_another_students_attempt_cannot_be_started_over(self):
        intruder = User.objects.create_user('ciaran', password='pw')
        self.client.force_login(intruder)

        response = self.restart()

        self.assertEqual(response.status_code, 404)
        self.attempt.refresh_from_db()
        self.assertFalse(self.attempt.is_completed)
