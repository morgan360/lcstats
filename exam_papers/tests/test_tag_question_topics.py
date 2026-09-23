"""Giving a question the topic its parts already say it is about.

A question with no topic is invisible in the homework picker and on the topic
pages however well its parts are tagged, which is how twenty deferred-paper
questions became unsettable.
"""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import Subject
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart
from interactive_lessons.models import Topic


class TagQuestionTopicsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.trig = Topic.objects.create(name='Trigonometry', subject=cls.maths, paper='p2')
        cls.functions = Topic.objects.create(name='Functions', subject=cls.maths, paper='p1')
        cls.paper = ExamPaper.objects.create(
            subject=cls.maths, year=2022, paper_type='p1', total_marks=300,
            is_published=True)

    def question(self, number, parts, topic=None):
        """parts: list of (topic, max_marks) in the order they appear."""
        question = ExamQuestion.objects.create(
            exam_paper=self.paper, question_number=number, topic=topic,
            total_marks=sum(m or 0 for _t, m in parts))
        for order, (part_topic, marks) in enumerate(parts, start=1):
            ExamQuestionPart.objects.create(
                question=question, label=f'({chr(96 + order)})', order=order,
                max_marks=marks, topic=part_topic)
        return question

    def run_command(self, *args):
        out = StringIO()
        call_command('tag_question_topics', *args, stdout=out)
        return out.getvalue()

    def test_the_topic_carrying_most_marks_wins(self):
        question = self.question(1, [(self.functions, 5), (self.trig, 20)])
        self.run_command()
        question.refresh_from_db()
        self.assertEqual(question.topic, self.trig)

    def test_a_tie_goes_to_the_topic_that_comes_first(self):
        question = self.question(2, [(self.functions, 10), (self.trig, 10)])
        self.run_command()
        question.refresh_from_db()
        self.assertEqual(question.topic, self.functions)

    def test_a_part_without_marks_still_counts_for_something(self):
        question = self.question(3, [(self.trig, None), (self.functions, None)])
        self.run_command()
        question.refresh_from_db()
        self.assertEqual(question.topic, self.trig)

    def test_a_question_with_no_tagged_parts_is_left_alone(self):
        question = self.question(4, [(None, 10), (None, 15)])
        output = self.run_command()
        question.refresh_from_db()
        self.assertIsNone(question.topic)
        self.assertIn('no part is tagged', output)

    def test_a_topic_already_set_is_kept(self):
        question = self.question(5, [(self.trig, 25)], topic=self.functions)
        self.run_command()
        question.refresh_from_db()
        self.assertEqual(question.topic, self.functions)

    def test_overwrite_replaces_it(self):
        question = self.question(6, [(self.trig, 25)], topic=self.functions)
        self.run_command('--overwrite')
        question.refresh_from_db()
        self.assertEqual(question.topic, self.trig)

    def test_a_dry_run_writes_nothing(self):
        question = self.question(7, [(self.trig, 25)])
        output = self.run_command('--dry-run')
        question.refresh_from_db()
        self.assertIsNone(question.topic)
        self.assertIn('nothing will be written', output)
        self.assertIn('Trigonometry', output)

    def test_it_can_be_limited_to_one_paper(self):
        other_paper = ExamPaper.objects.create(
            subject=self.maths, year=2021, paper_type='p1', total_marks=300,
            is_published=True)
        mine = self.question(8, [(self.trig, 25)])
        theirs = ExamQuestion.objects.create(
            exam_paper=other_paper, question_number=8, total_marks=25)
        ExamQuestionPart.objects.create(
            question=theirs, label='(a)', order=1, max_marks=25, topic=self.trig)

        self.run_command('--paper', str(self.paper.id))
        mine.refresh_from_db()
        theirs.refresh_from_db()
        self.assertEqual(mine.topic, self.trig)
        self.assertIsNone(theirs.topic)
