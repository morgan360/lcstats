"""Starting one practice question over, without losing the answers already given."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Subject
from exam_papers.models import (ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionAttempt,
                                ExamQuestionPart, QuestionRestart)


class QuestionRestartTests(TestCase):
    def setUp(self):
        maths, _ = Subject.objects.get_or_create(slug='maths', defaults={'name': 'Maths'})
        self.paper = ExamPaper.objects.create(subject=maths, year=2025, paper_type='p1',
                                              total_marks=300, is_published=True)
        self.question = ExamQuestion.objects.create(exam_paper=self.paper, question_number=2,
                                                    total_marks=25, order=2)
        self.other = ExamQuestion.objects.create(exam_paper=self.paper, question_number=3,
                                                 total_marks=25, order=3)
        self.part = ExamQuestionPart.objects.create(question=self.question, label='(a)',
                                                    max_marks=15, order=1)
        self.other_part = ExamQuestionPart.objects.create(question=self.other, label='(a)',
                                                          max_marks=10, order=1)
        self.student = User.objects.create_user('ruairi', password='pw')
        self.client.force_login(self.student)
        self.attempt = ExamAttempt.objects.create(student=self.student, exam_paper=self.paper)

    def answer(self, part, text, minutes_ago=5):
        row = ExamQuestionAttempt.objects.create(
            exam_attempt=self.attempt, question_part=part, student_answer=text,
            marks_awarded=5, max_marks=part.max_marks)
        ExamQuestionAttempt.objects.filter(id=row.id).update(
            submitted_at=timezone.now() - timedelta(minutes=minutes_ago))

    def restart(self, attempt=None, question=None):
        return self.client.post(reverse('exam_papers:restart_question', args=[
            (attempt or self.attempt).id, (question or self.question).id]))

    def page(self, question=None):
        return self.client.get(reverse('exam_papers:question_interface', args=[
            self.attempt.id, (question or self.question).id]))

    def part_data(self, response):
        return response.context['parts_with_attempts'][0]

    def test_starting_over_empties_the_boxes_and_locks_the_solution(self):
        self.answer(self.part, 'y=4x')
        self.answer(self.part, 'y=4x+6')

        response = self.restart()
        self.assertRedirects(response, reverse('exam_papers:question_interface',
                                               args=[self.attempt.id, self.question.id]))

        data = self.part_data(self.page())
        self.assertIsNone(data['latest_attempt'])
        self.assertEqual(data['attempt_count'], 0)
        self.assertFalse(data['solution_unlocked'])

    def test_the_earlier_answers_are_kept_for_homework_and_reports(self):
        self.answer(self.part, 'y=4x')

        self.restart()

        self.assertEqual(ExamQuestionAttempt.objects.filter(question_part=self.part).count(), 1)

    def test_answers_after_the_restart_count_again(self):
        self.answer(self.part, 'y=4x', minutes_ago=10)
        self.restart()
        self.answer(self.part, 'y=4x+6', minutes_ago=-1)

        data = self.part_data(self.page())

        self.assertEqual(data['attempt_count'], 1)
        self.assertEqual(data['latest_attempt'].student_answer, 'y=4x+6')

    def test_the_locked_solution_is_refused_after_starting_over(self):
        self.answer(self.part, 'a')
        self.answer(self.part, 'b')
        self.restart()

        response = self.client.get(reverse('exam_papers:get_solution',
                                           args=[self.attempt.id, self.part.id]))

        self.assertFalse(response.json()['success'])

    def test_other_questions_are_left_alone(self):
        self.answer(self.other_part, 'x=2')

        self.restart()

        self.assertEqual(self.part_data(self.page(self.other))['attempt_count'], 1)

    def test_a_second_restart_moves_the_first_forward(self):
        self.restart()
        self.restart()

        self.assertEqual(QuestionRestart.objects.count(), 1)

    def test_a_timed_exam_question_is_not_started_over_alone(self):
        timed = ExamAttempt.objects.create(student=self.student, exam_paper=self.paper,
                                           attempt_mode='full_timed')

        self.restart(attempt=timed)

        self.assertFalse(QuestionRestart.objects.exists())

    def test_another_students_question_cannot_be_started_over(self):
        self.client.force_login(User.objects.create_user('orla', password='pw'))

        response = self.restart()

        self.assertEqual(response.status_code, 404)
        self.assertFalse(QuestionRestart.objects.exists())

    def test_the_button_is_on_practice_questions(self):
        self.assertContains(self.page(), 'Start this question over')

    # The question card on a topic's exam questions page
    def best(self):
        from exam_papers.services.topic_questions import best_part_attempts
        return best_part_attempts(self.student, [self.part]).get(self.part.id)

    def test_the_score_after_a_restart_is_the_new_one(self):
        self.answer(self.part, 'y=4x+6', minutes_ago=10)
        ExamQuestionAttempt.objects.filter(question_part=self.part).update(marks_awarded=15)
        self.restart()
        self.answer(self.part, 'y=4x-6', minutes_ago=-1)  # 5 marks

        best = self.best()

        self.assertEqual(best['best'].marks_awarded, 5)
        self.assertEqual(best['count'], 1)

    def test_a_restarted_question_not_yet_answered_again_shows_no_score(self):
        self.answer(self.part, 'y=4x+6')
        self.restart()

        self.assertIsNone(self.best())
