"""Exam stamp cards: a MicroBadge per question once every part is attempted,
and a paper badge once every question on the paper has one."""
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.models import Subject
from exam_papers.models import (
    ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionAttempt, ExamQuestionPart,
)
from studyplans.services import exam_stamps


class ExamStampTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.student = User.objects.create_user('aoife', password='pw')
        Group.objects.get_or_create(name='Students')[0].user_set.add(cls.student)

        cls.p1 = ExamPaper.objects.create(subject=cls.maths, year=2025, paper_type='p1',
                                          total_marks=300, is_published=True)
        cls.p2 = ExamPaper.objects.create(subject=cls.maths, year=2025, paper_type='p2',
                                          total_marks=300, is_published=True)
        cls.older = ExamPaper.objects.create(subject=cls.maths, year=2024, paper_type='p1',
                                             total_marks=300, is_published=True)
        ExamPaper.objects.create(subject=cls.maths, year=2025, paper_type='p1',
                                 total_marks=300, is_published=True, is_deferred=True)

        cls.q1 = ExamQuestion.objects.create(exam_paper=cls.p1, question_number=1, total_marks=20)
        cls.q2 = ExamQuestion.objects.create(exam_paper=cls.p1, question_number=2, total_marks=20)
        cls.q1a = ExamQuestionPart.objects.create(question=cls.q1, label='(a)', order=1, max_marks=10)
        cls.q1b = ExamQuestionPart.objects.create(question=cls.q1, label='(b)', order=2, max_marks=10)
        cls.q2a = ExamQuestionPart.objects.create(question=cls.q2, label='(a)', order=1, max_marks=20)

    def attempt(self, *parts):
        exam_attempt = ExamAttempt.objects.create(
            student=self.student, exam_paper=self.p1,
            attempt_mode='question_practice', total_marks_possible=300)
        for part in parts:
            ExamQuestionAttempt.objects.create(
                exam_attempt=exam_attempt, question_part=part, max_marks=10)

    def row(self, paper):
        return next(r for r in exam_stamps.rows_for(self.student, self.maths)
                    if r['paper'] == paper)

    def test_rows_run_newest_first_paper_1_before_paper_2_without_deferred(self):
        papers = [r['paper'] for r in exam_stamps.rows_for(self.student, self.maths)]
        self.assertEqual(papers, [self.p1, self.p2, self.older])

    def test_every_row_has_ten_question_columns(self):
        row = self.row(self.p1)
        self.assertEqual(len(row['cells']), 10)
        self.assertEqual(row['total'], 2)
        self.assertIsNone(row['cells'][2]['question'])

    def test_a_partly_attempted_question_is_not_stamped(self):
        self.attempt(self.q1a)
        self.assertFalse(self.row(self.p1)['cells'][0]['stamped'])

    def test_every_part_attempted_stamps_it_whatever_the_score(self):
        self.attempt(self.q1a, self.q1b)
        row = self.row(self.p1)
        self.assertTrue(row['cells'][0]['stamped'])
        self.assertEqual(row['earned'], 1)
        self.assertFalse(row['stamped'])

    def test_every_question_stamped_earns_the_paper_badge(self):
        self.attempt(self.q1a, self.q1b)
        self.attempt(self.q2a)
        self.assertTrue(self.row(self.p1)['stamped'])

    def test_a_paper_with_no_questions_never_earns_its_badge(self):
        self.assertFalse(self.row(self.p2)['stamped'])

    def test_the_tab_renders(self):
        self.attempt(self.q1a, self.q1b)
        self.client.force_login(self.student)
        response = self.client.get(reverse('studyplans:stamp_cards'), {'tab': 'exams'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2025 Paper 1')
        self.assertContains(response, 'MicroBadge earned')
        self.assertContains(response, reverse('exam_papers:practise_question',
                                              args=[self.q2.id]))
