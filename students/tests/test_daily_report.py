"""The daily report covers every kind of activity, AI Help included."""
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.models import Subject
from exam_papers.models import ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionAttempt, ExamQuestionPart
from interactive_lessons.models import Question, Topic
from notes.models import InfoBotQuery
from students.models import QuestionAttempt, StudentProfile


class DailyReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(name='Algebra', subject=maths, paper='p1')
        cls.question = Question.objects.create(topic=cls.topic, order=1)
        paper = ExamPaper.objects.create(subject=maths, year=2022, paper_type='p1',
                                         total_marks=300, is_published=True)
        cls.part = ExamQuestionPart.objects.create(
            question=ExamQuestion.objects.create(exam_paper=paper, question_number=10,
                                                 total_marks=50),
            label='(c)', max_marks=10, order=3)
        cls.francesco = User.objects.create_user('francesco', first_name='Francesco',
                                                 last_name='Nagni')
        cls.ann = User.objects.create_user('ann')

    def report(self, *args):
        out = StringIO()
        call_command('daily_student_report', '--dry-run', *args, stdout=out)
        return out.getvalue()

    def test_a_student_with_only_exam_work_and_ai_help_is_reported(self):
        attempt = ExamAttempt.objects.create(student=self.francesco,
                                             exam_paper=self.part.question.exam_paper)
        ExamQuestionAttempt.objects.create(exam_attempt=attempt, question_part=self.part,
                                           marks_awarded=7, max_marks=10)
        InfoBotQuery.objects.create(user=self.francesco, question='come si calcola',
                                    exam_question_id=self.part.question_id,
                                    question_part_id=self.part.id)

        text = self.report()
        self.assertIn('Francesco Nagni (francesco)', text)
        self.assertIn('Exam part answers 1', text)
        self.assertIn('AI Help questions 1', text)
        self.assertIn(f'Asked AI Help about {self.part}: "come si calcola"', text)
        self.assertIn('AI Help Questions Asked: 1', text)
        self.assertIn('Active Students: 1', text)

    def test_lesson_stats_are_still_reported(self):
        QuestionAttempt.objects.create(student=StudentProfile.objects.get(user=self.ann),
                                       question=self.question, student_answer='x',
                                       is_correct=True, score_awarded=100)
        text = self.report()
        self.assertIn('ann (ann)', text)
        self.assertIn('Attempts: 1', text)
        self.assertIn('Correct: 1 (100.0%)', text)

    def test_an_excluded_user_is_left_out_of_every_section(self):
        InfoBotQuery.objects.create(user=self.ann, question='help')
        text = self.report('--exclude-user', 'ann')
        self.assertNotIn('ann (ann)', text)
        self.assertIn('No student activity in this period.', text)
