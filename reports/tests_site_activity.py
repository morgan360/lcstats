"""The Today page: one day's activity across the site, per student."""
from datetime import datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Subject
from exam_papers.models import ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionAttempt, ExamQuestionPart
from interactive_lessons.models import Question, Topic
from notes.models import InfoBotQuery
from students.models import LoginHistory, QuestionAttempt, StudentProfile

from .activity import activity_for_day


def at(day, hour, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


class SiteActivityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('admin', password='pw')
        cls.teacher = User.objects.create_user('teacher', password='pw', is_staff=True)
        cls.ann = User.objects.create_user('ann', password='pw', first_name='Ann', last_name='Byrne')
        cls.bob = User.objects.create_user('bob', password='pw')

        maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(name='Algebra', subject=maths, paper='p1')
        cls.question = Question.objects.create(topic=cls.topic, order=3)
        paper = ExamPaper.objects.create(subject=maths, year=2024, paper_type='p1',
                                         total_marks=300, is_published=True)
        exam_question = ExamQuestion.objects.create(exam_paper=paper, question_number=2,
                                                    total_marks=30)
        cls.part = ExamQuestionPart.objects.create(question=exam_question, label='(b)',
                                                   max_marks=10, order=2)
        cls.today = timezone.localdate()
        cls.yesterday = cls.today - timedelta(days=1)

    def lesson(self, user, when, correct=True):
        return QuestionAttempt.objects.create(
            student=StudentProfile.objects.get(user=user), question=self.question,
            student_answer='x', is_correct=correct, attempted_at=when)

    def exam(self, user, when, marks):
        attempt = ExamAttempt.objects.create(
            student=user, exam_paper=self.part.question.exam_paper)
        row = ExamQuestionAttempt.objects.create(
            exam_attempt=attempt, question_part=self.part, student_answer='y',
            marks_awarded=marks, max_marks=10)
        ExamQuestionAttempt.objects.filter(pk=row.pk).update(submitted_at=when)

    def login(self, user, when, success=True):
        row = LoginHistory.objects.create(
            user=user if success else None, username_attempted=user.username,
            success=success)
        LoginHistory.objects.filter(pk=row.pk).update(timestamp=when)

    def test_one_timeline_per_student_in_time_order(self):
        self.login(self.ann, at(self.today, 9))
        self.exam(self.ann, at(self.today, 9, 30), marks=7)
        self.lesson(self.ann, at(self.today, 9, 10), correct=False)

        result = activity_for_day(self.today)
        [ann] = result['students']
        self.assertEqual(ann.user, self.ann)
        self.assertEqual([e.kind for e in ann.events], ['login', 'lesson', 'exam'])
        self.assertEqual(ann.events[1].outcome, 'bad')
        self.assertIn('Algebra: Q3', ann.events[1].text)
        self.assertIn('(b) - 7/10', ann.events[2].text)
        self.assertEqual(ann.counts, [('Logins', 1), ('Lesson answers', 1),
                                      ('Exam part answers', 1)])

    def test_exam_rows_are_coloured_by_marks(self):
        self.exam(self.ann, at(self.today, 9), marks=10)
        self.exam(self.ann, at(self.today, 10), marks=7)
        self.exam(self.ann, at(self.today, 11), marks=0)
        [ann] = activity_for_day(self.today)['students']
        self.assertEqual([e.outcome for e in ann.events], ['good', 'partial', 'bad'])

    def test_only_the_chosen_day_counts(self):
        self.lesson(self.ann, at(self.yesterday, 23, 59))
        self.lesson(self.bob, at(self.today, 0, 1))

        self.assertEqual([s.user for s in activity_for_day(self.today)['students']],
                         [self.bob])
        self.assertEqual([s.user for s in activity_for_day(self.yesterday)['students']],
                         [self.ann])

    def test_most_recently_active_student_comes_first(self):
        self.lesson(self.ann, at(self.today, 8))
        self.lesson(self.bob, at(self.today, 10))
        self.assertEqual([s.user for s in activity_for_day(self.today)['students']],
                         [self.bob, self.ann])

    def test_staff_are_left_out_unless_asked_for(self):
        self.login(self.teacher, at(self.today, 8))
        self.assertEqual(activity_for_day(self.today)['students'], [])
        self.assertEqual(len(activity_for_day(self.today, include_staff=True)['students']), 1)

    def test_failed_logins_are_listed_apart_from_students(self):
        self.login(self.bob, at(self.today, 7), success=False)
        result = activity_for_day(self.today)
        self.assertEqual(result['students'], [])
        self.assertEqual([r.username_attempted for r in result['failed_logins']], ['bob'])

    def test_page_is_superuser_only(self):
        url = reverse('reports:site_activity')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_page_shows_a_chosen_day_and_never_the_future(self):
        self.lesson(self.ann, at(self.yesterday, 11))
        self.client.force_login(self.admin)
        url = reverse('reports:site_activity')

        response = self.client.get(url, {'date': self.yesterday.isoformat()})
        self.assertContains(response, 'Ann Byrne')
        self.assertEqual(response.context['next_day'], self.today)

        response = self.client.get(url, {'date': (self.today + timedelta(days=3)).isoformat()})
        self.assertEqual(response.context['day'], self.today)
        self.assertIsNone(response.context['next_day'])

        response = self.client.get(url, {'date': 'rubbish'})
        self.assertEqual(response.context['day'], self.today)

    def test_ai_help_questions_show_with_the_part_they_were_about(self):
        InfoBotQuery.objects.create(
            user=self.ann, question='how do I   start this?', created_at=at(self.today, 9),
            exam_question_id=self.part.question_id, question_part_id=self.part.id)
        InfoBotQuery.objects.create(question='asked before users were recorded',
                                    created_at=at(self.today, 10))

        [ann] = activity_for_day(self.today)['students']
        [event] = ann.events
        self.assertEqual(event.kind, 'ai_help')
        self.assertEqual(event.text,
                         f'Asked AI Help about {self.part}: "how do I start this?"')

    def test_ai_help_records_who_asked(self):
        note = SimpleNamespace(content='Factorise first.', title='Factorising')
        self.client.force_login(self.ann)
        with patch('interactive_lessons.views.match_note', return_value=(note, 0.95, [])):
            response = self.client.get(
                reverse('info_bot', args=['algebra']), {'query': 'help'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(InfoBotQuery.objects.get().user, self.ann)
