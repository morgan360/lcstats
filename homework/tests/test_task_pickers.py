"""What the homework pickers offer, and how they name it.

A question files under one dominant topic while its parts carry their own, so
picking by the question's topic alone hid questions a teacher could see on the
topic page -- 2022 Paper 1 Q8 is filed under Trig with its parts tagged
Functions and Integration.
"""
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Subject
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart
from homework.forms import ExamQuestionsTaskForm
from interactive_lessons.models import Topic


class PickerTestBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.trig = Topic.objects.create(name='Trigonometry', subject=cls.maths, paper='p2')
        cls.functions = Topic.objects.create(name='Functions', subject=cls.maths, paper='p1')
        cls.integration = Topic.objects.create(name='Integration', subject=cls.maths, paper='p1')

        cls.paper = ExamPaper.objects.create(
            subject=cls.maths, year=2022, paper_type='p1', total_marks=300,
            is_published=True)
        cls.deferred = ExamPaper.objects.create(
            subject=cls.maths, year=2022, paper_type='p1', total_marks=300,
            is_published=True, is_deferred=True)

        # Filed under Trig, but its parts are Functions and Integration.
        cls.q8 = ExamQuestion.objects.create(
            exam_paper=cls.paper, question_number=8, topic=cls.trig, total_marks=25)
        ExamQuestionPart.objects.create(
            question=cls.q8, label='(a)', order=1, max_marks=10, topic=cls.functions)
        ExamQuestionPart.objects.create(
            question=cls.q8, label='(b)', order=2, max_marks=15, topic=cls.integration)

        cls.deferred_q8 = ExamQuestion.objects.create(
            exam_paper=cls.deferred, question_number=8, topic=cls.trig, total_marks=25)

    def form_for(self, topic):
        """The inline's form as the formset builds it: topic off the parent."""
        return ExamQuestionsTaskForm(
            parent_assignment=SimpleNamespace(topic=topic))

    def offered(self, topic):
        return list(self.form_for(topic).fields['exam_question'].queryset)


class ExamQuestionPickerTests(PickerTestBase):

    def test_a_question_is_not_offered_where_no_part_is_on_the_topic(self):
        """Its own tag says Trig, but a teacher setting it for Trig would be
        setting two parts of Functions and Integration."""
        self.assertNotIn(self.q8, self.offered(self.trig))

    def test_a_question_with_untagged_parts_falls_back_to_its_own_topic(self):
        self.q8.parts.update(topic=None)
        self.assertIn(self.q8, self.offered(self.trig))

    def test_and_under_any_topic_its_parts_carry(self):
        self.assertIn(self.q8, self.offered(self.functions))
        self.assertIn(self.q8, self.offered(self.integration))

    def test_it_is_offered_once_however_many_parts_match(self):
        ExamQuestionPart.objects.create(
            question=self.q8, label='(c)', order=3, max_marks=5, topic=self.functions)
        self.assertEqual(self.offered(self.functions).count(self.q8), 1)

    def test_an_unrelated_topic_does_not_get_it(self):
        other = Topic.objects.create(name='Probability', subject=self.maths, paper='p2')
        self.assertNotIn(self.q8, self.offered(other))

    def test_the_label_names_the_paper_and_the_sitting(self):
        field = self.form_for(self.trig).fields['exam_question']
        self.assertEqual(field.label_from_instance(self.q8),
                         '[Maths] 2022 Paper 1 Q8 - Trigonometry')
        self.assertIn('(Deferred)', field.label_from_instance(self.deferred_q8))


class TopicFilterEndpointTests(PickerTestBase):
    """The dropdown a teacher actually sees once they pick a topic is built by
    this endpoint, not by the form, so it must offer exactly the same thing."""

    def setUp(self):
        staff = User.objects.create_user('ms_teacher', password='pw', is_staff=True)
        staff.is_superuser = True
        staff.save()
        self.client.force_login(staff)

    def payload(self, topic):
        response = self.client.get(
            reverse('homework:topic_content_options', args=[topic.id]))
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_it_offers_a_question_through_its_parts(self):
        ids = [o['id'] for o in self.payload(self.functions)['exam_question']]
        self.assertIn(self.q8.id, ids)

    def test_each_question_appears_once(self):
        ids = [o['id'] for o in self.payload(self.functions)['exam_question']]
        self.assertEqual(len(ids), len(set(ids)))

    def test_it_labels_them_like_the_form_does(self):
        option = next(o for o in self.payload(self.functions)['exam_question']
                      if o['id'] == self.q8.id)
        field = self.form_for(self.functions).fields['exam_question']
        self.assertEqual(option['label'], field.label_from_instance(self.q8))

    def test_an_unknown_topic_is_a_404(self):
        response = self.client.get(
            reverse('homework:topic_content_options', args=[999999]))
        self.assertEqual(response.status_code, 404)
