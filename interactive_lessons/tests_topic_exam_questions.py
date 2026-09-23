"""The topic's exam question list, as a student reads it.

A question is listed when the topic is its own or any of its parts'. What it
shows underneath is only the parts on that topic: the greyed-out others said
"here is work that is not yours", which is a puzzle rather than information.
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

    def test_it_offers_the_parts_on_this_topic(self):
        response = self.page(self.trig)
        self.assertContains(
            response, f'name="part_id" value="{self.trig_part.id}"')
        self.assertContains(response, 'Practise this part')

    def test_it_does_not_list_parts_belonging_to_other_topics(self):
        response = self.page(self.trig)
        self.assertNotContains(
            response, f'name="part_id" value="{self.other_part.id}"')

    def test_a_question_with_no_part_on_the_topic_is_not_listed(self):
        """Q8 is filed under Trig but every part of it is Functions, so there is
        nothing on this page for a student to do with it."""
        response = self.page(self.trig)
        self.assertContains(response, 'Question 3')
        self.assertNotContains(response, 'Question 8')
        for part in self.whole.parts.all():
            self.assertNotContains(
                response, f'name="part_id" value="{part.id}"')

    def test_a_question_whose_parts_are_untagged_still_lists(self):
        for part in self.mixed.parts.all():
            part.topic = None
            part.save(update_fields=['topic'])
        response = self.page(self.trig)
        self.assertContains(response, 'Question 3')
        self.assertContains(response, 'Practice This Question')
