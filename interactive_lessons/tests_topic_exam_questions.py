"""The topic's exam question list, as a student reads it.

Whole questions only, listed by the question's own topics; a part's topic no
longer decides anything here.
"""
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.models import Subject
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart
from interactive_lessons.models import Topic


class TopicExamQuestionsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.trig = Topic.objects.create(name='Trigonometry', subject=cls.maths, paper='p2')
        cls.functions = Topic.objects.create(name='Functions', subject=cls.maths, paper='p1')
        cls.student = User.objects.create_user('aoife', password='pw')
        Group.objects.get_or_create(name='Students')[0].user_set.add(cls.student)

        cls.paper = ExamPaper.objects.create(
            subject=cls.maths, year=2022, paper_type='p1', total_marks=300,
            is_published=True)

        # Its own topic is Trig; one part is Trig, one is Functions.
        cls.mixed = ExamQuestion.objects.create(
            exam_paper=cls.paper, question_number=3, topic=cls.trig, total_marks=30)
        cls.other_part = ExamQuestionPart.objects.create(
            question=cls.mixed, label='(a)', order=1, max_marks=20, topic=cls.functions)
        cls.trig_part = ExamQuestionPart.objects.create(
            question=cls.mixed, label='(b)', order=2, max_marks=10, topic=cls.trig)

        # Filed under Trig, but no part is tagged Trig.
        cls.whole = ExamQuestion.objects.create(
            exam_paper=cls.paper, question_number=8, topic=cls.trig, total_marks=50)
        for order, label in enumerate(['(a)', '(b)', '(c)'], start=1):
            ExamQuestionPart.objects.create(
                question=cls.whole, label=label, order=order, max_marks=10,
                topic=cls.functions)

    def setUp(self):
        self.client.force_login(self.student)

    def page(self, topic):
        response = self.client.get(
            reverse('topic_exam_questions', args=[topic.slug]))
        self.assertEqual(response.status_code, 200)
        return response

    def test_it_lists_questions_under_their_main_topic(self):
        response = self.page(self.trig)
        self.assertContains(response, 'Question 3')
        self.assertContains(response, 'Question 8')
        self.assertContains(response, 'Practice This Question')

    def test_it_no_longer_offers_single_parts(self):
        response = self.page(self.trig)
        self.assertNotContains(response, 'name="part_id"')
        self.assertNotContains(response, 'Practise this part')

    def test_part_tags_do_not_list_a_question(self):
        """Q3 has a Functions part, but Functions is not one of its topics."""
        self.assertNotContains(self.page(self.functions), 'Question 3')
