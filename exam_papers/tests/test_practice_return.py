"""Leaving question practice goes back to where the student came from."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Subject
from exam_papers.models import ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionPart

HOMEWORK = 'http://testserver/homework/'


class PracticeReturnTests(TestCase):
    def setUp(self):
        maths, _ = Subject.objects.get_or_create(slug='maths', defaults={'name': 'Maths'})
        self.paper = ExamPaper.objects.create(subject=maths, year=2019, paper_type='p2',
                                              total_marks=300, is_published=True)
        self.q1, self.q2 = (
            ExamQuestion.objects.create(exam_paper=self.paper, question_number=n,
                                        total_marks=25, order=n)
            for n in (1, 2))
        for q in (self.q1, self.q2):
            ExamQuestionPart.objects.create(question=q, label='(a)', max_marks=10, order=1)
        self.client.force_login(User.objects.create_user('saoirse', password='pw'))

    def open(self, question, referer=None):
        """Open a question for practice the way homework links do."""
        extra = {'HTTP_REFERER': referer} if referer else {}
        return self.client.get(reverse('exam_papers:practise_question', args=[question.id]),
                               follow=True, **extra)

    def test_back_returns_to_the_page_the_student_came_from(self):
        response = self.open(self.q1, referer=HOMEWORK + '?class=3')

        self.assertEqual(response.context['return_url'], '/homework/?class=3')
        self.assertContains(response, 'href="/homework/?class=3"')

    def test_moving_to_the_next_question_keeps_the_way_back(self):
        first = self.open(self.q1, referer=HOMEWORK)
        attempt = first.context['attempt']
        question_page = 'http://testserver' + reverse(
            'exam_papers:question_interface', args=[attempt.id, self.q1.id])

        response = self.client.get(
            reverse('exam_papers:question_interface', args=[attempt.id, self.q2.id]),
            HTTP_REFERER=question_page)

        self.assertEqual(response.context['return_url'], '/homework/')

    def test_with_no_known_origin_back_goes_to_the_paper(self):
        response = self.open(self.q1)

        self.assertIsNone(response.context['return_url'])
        self.assertContains(response, 'href="%s"' % reverse(
            'exam_papers:paper_detail', args=[self.paper.slug]))

    def test_another_site_is_never_a_way_back(self):
        response = self.open(self.q1, referer='https://evil.example/phish')

        self.assertIsNone(response.context['return_url'])

    def test_the_login_page_is_not_a_way_back(self):
        response = self.open(self.q1, referer='http://testserver/accounts/login/?next=/x/')

        self.assertIsNone(response.context['return_url'])

    def test_timed_exams_have_no_back_link(self):
        attempt = ExamAttempt.objects.create(student=User.objects.get(username='saoirse'),
                                             exam_paper=self.paper, attempt_mode='full_timed')

        response = self.client.get(
            reverse('exam_papers:question_interface', args=[attempt.id, self.q1.id]),
            HTTP_REFERER=HOMEWORK)

        self.assertIsNone(response.context['return_url'])
        self.assertNotContains(response, 'practice-back"')
