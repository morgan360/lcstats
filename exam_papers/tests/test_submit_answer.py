"""A double click on Check Answer is one submission, not two tries."""
import json
import threading
import time
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Subject
from exam_papers.models import ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionAttempt, ExamQuestionPart

GRADER = 'exam_papers.views.grade_with_vision_marking_scheme'


def graded(**_):
    return {'marks_awarded': 0, 'is_correct': False, 'feedback': 'Not quite.', 'max_marks': 10}


def slow_graded(**kwargs):
    time.sleep(1)  # long enough for a second click to land mid-marking
    return graded(**kwargs)


class SubmitSetup:
    def make(self):
        maths, _ = Subject.objects.get_or_create(slug='maths', defaults={'name': 'Maths'})
        paper = ExamPaper.objects.create(subject=maths, year=2022, paper_type='p1',
                                         total_marks=300, is_published=True)
        question = ExamQuestion.objects.create(exam_paper=paper, question_number=10,
                                               total_marks=50)
        self.part = ExamQuestionPart.objects.create(question=question, label='(d)',
                                                    max_marks=10, order=4)
        self.student = User.objects.create_user('francesco', password='pw')
        self.attempt = ExamAttempt.objects.create(student=self.student, exam_paper=paper)
        self.url = reverse('exam_papers:submit_answer', args=[self.attempt.id])

    def submit(self, answer, client=None):
        client = client or self.client
        response = client.post(self.url, json.dumps({'part_id': self.part.id, 'answer': answer}),
                               content_type='application/json')
        return response.json()

    def rows(self):
        return list(ExamQuestionAttempt.objects.filter(question_part=self.part)
                    .order_by('id').values_list('attempt_number', flat=True))


class SubmitAnswerTests(SubmitSetup, TestCase):
    def setUp(self):
        self.make()
        self.client.force_login(self.student)

    def test_the_same_answer_twice_in_a_row_is_saved_and_marked_once(self):
        with patch(GRADER, side_effect=graded) as grader:
            first = self.submit('2')
            second = self.submit('2')
        self.assertEqual(grader.call_count, 1)
        self.assertEqual(self.rows(), [1])
        self.assertFalse(first['duplicate'])
        self.assertTrue(second['duplicate'])
        self.assertEqual(second['attempt_number'], 1)
        self.assertFalse(second['solution_unlocked'])  # still one try, threshold is 2

    def test_a_different_answer_straight_away_is_a_new_try(self):
        with patch(GRADER, side_effect=graded):
            self.submit('2')
            result = self.submit('3')
        self.assertEqual(self.rows(), [1, 2])
        self.assertTrue(result['solution_unlocked'])

    def test_the_same_answer_again_later_is_a_new_try(self):
        with patch(GRADER, side_effect=graded):
            self.submit('2')
            ExamQuestionAttempt.objects.update(submitted_at=timezone.now() - timedelta(seconds=30))
            result = self.submit('2')
        self.assertEqual(self.rows(), [1, 2])
        self.assertFalse(result['duplicate'])


class ConcurrentSubmitTests(SubmitSetup, TransactionTestCase):
    """The real bug: the second request arrives while the first is still being
    marked, so neither has saved when the other counts earlier tries."""

    # A TransactionTestCase empties every table afterwards, including the rows
    # data migrations seed (the Maths subject). serialized_rollback only puts
    # them back at the start of the next such test, so after the last one they
    # stay gone - and with --keepdb, gone for every later run. Restore them
    # straight after this test's own flush instead.
    serialized_rollback = True

    def _fixture_teardown(self):
        super()._fixture_teardown()
        connection.creation.deserialize_db_from_string(
            connection._test_serialized_contents)

    def setUp(self):
        self.make()

    def test_two_clicks_during_marking_make_one_try(self):
        results = []

        def click():
            client = Client()
            client.force_login(self.student)
            try:
                results.append(self.submit('2', client))
            finally:
                connection.close()

        with patch(GRADER, side_effect=slow_graded) as grader:
            threads = [threading.Thread(target=click) for _ in range(2)]
            for thread in threads:
                thread.start()
                time.sleep(0.2)
            for thread in threads:
                thread.join()

        self.assertEqual(self.rows(), [1])
        self.assertEqual(grader.call_count, 1)
        self.assertEqual(sorted(r['duplicate'] for r in results), [False, True])
        self.assertTrue(all(r['attempt_number'] == 1 for r in results))
