"""Part-level topics: a question shows on the topic any of its parts is filed
under, a single part can be opened on its own, and the classifier writes one
topic per part.
"""
import json
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from core.models import Subject
from exam_papers.models import ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionPart
from interactive_lessons.models import Topic


class PartTopicsTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.functions = Topic.objects.create(name='Functions', subject=cls.maths, paper='p1')
        cls.calculus = Topic.objects.create(name='Differential Calculus', subject=cls.maths, paper='p1')
        cls.finance = Topic.objects.create(name='Finance', subject=cls.maths, paper='p1')

        cls.paper = ExamPaper.objects.create(
            subject=cls.maths, year=2019, paper_type='p1',
            total_marks=300, is_published=True,
        )
        cls.question = ExamQuestion.objects.create(
            exam_paper=cls.paper, question_number=6, topic=cls.functions, total_marks=30,
        )
        cls.part_a = ExamQuestionPart.objects.create(
            question=cls.question, label='(a)', max_marks=10, order=1)
        cls.part_b = ExamQuestionPart.objects.create(
            question=cls.question, label='(b)', max_marks=20, order=2)
        cls.part_a.topic = cls.functions
        cls.part_a.save(update_fields=['topic'])
        cls.part_b.topic = cls.calculus
        cls.part_b.save(update_fields=['topic'])

        cls.other_question = ExamQuestion.objects.create(
            exam_paper=cls.paper, question_number=7, topic=cls.finance, total_marks=30,
        )
        cls.other_part = ExamQuestionPart.objects.create(
            question=cls.other_question, label='(a)', max_marks=30, order=1)

        cls.student = User.objects.create_user('student', password='pw')
        cls.staff = User.objects.create_user('teacher', password='pw', is_staff=True)
        cls.admin = User.objects.create_superuser('admin', password='pw')


class TopicPageTests(PartTopicsTestBase):
    def setUp(self):
        self.client.force_login(self.student)

    def page(self, topic):
        return self.client.get(reverse('topic_exam_questions', args=[topic.slug]))

    def test_question_appears_under_a_topic_only_one_part_is_on(self):
        response = self.page(self.calculus)
        questions = [q for group in response.context['questions_by_paper'].values()
                     for q in group['questions']]
        self.assertEqual(questions, [self.question])
        self.assertEqual(questions[0].matching_parts, [self.part_b])
        self.assertContains(response, 'name="part_id" value="%d"' % self.part_b.id)
        self.assertNotContains(response, 'name="part_id" value="%d"' % self.part_a.id)

    def test_question_is_listed_once_when_two_parts_share_a_topic(self):
        self.part_b.topic = self.functions
        self.part_b.save(update_fields=['topic'])

        response = self.page(self.functions)
        self.assertEqual(response.context['total_questions'], 1)
        self.assertEqual(response.context['total_parts'], 2)
        questions = [q for group in response.context['questions_by_paper'].values()
                     for q in group['questions']]
        self.assertEqual(questions[0].matching_parts, [self.part_a, self.part_b])

    def test_a_question_drops_off_a_topic_none_of_its_parts_is_on(self):
        """The parts decide. A question whose own tag says Functions while both
        its parts are Calculus has nothing on the Functions page: it would show
        as a question with no part a student could click."""
        self.part_a.topic = self.calculus
        self.part_a.save(update_fields=['topic'])

        response = self.page(self.functions)
        questions = [q for group in response.context['questions_by_paper'].values()
                     for q in group['questions']]
        self.assertEqual(questions, [])

    def test_its_own_topic_still_counts_while_no_part_is_tagged(self):
        """The fallback, for a question whose parts carry no topic at all."""
        for part in self.question.parts.all():
            part.topic = None
            part.save(update_fields=['topic'])

        response = self.page(self.functions)
        questions = [q for group in response.context['questions_by_paper'].values()
                     for q in group['questions']]
        self.assertEqual(questions, [self.question])
        self.assertEqual(questions[0].matching_parts, [])


class FocusedPartTests(PartTopicsTestBase):
    def setUp(self):
        self.client.force_login(self.student)

    def start(self, part):
        return self.client.post(
            reverse('exam_papers:start_paper_attempt', args=[self.paper.slug]),
            {'mode': 'question_practice', 'question_id': self.question.id, 'part_id': part.id},
        )

    def test_part_is_carried_through_to_the_interface(self):
        response = self.start(self.part_b)
        self.assertTrue(response['Location'].endswith(f'?part={self.part_b.id}'))

        page = self.client.get(response['Location'])
        self.assertEqual(page.context['focus_part'], self.part_b)
        self.assertContains(page, "You're answering part")
        focused = [p['part'] for p in page.context['parts_with_attempts'] if p['is_focused']]
        self.assertEqual(focused, [self.part_b])

    def test_part_from_another_question_is_ignored(self):
        response = self.start(self.other_part)
        self.assertNotIn('?part=', response['Location'])

    def test_unknown_part_in_url_shows_whole_question(self):
        attempt = ExamAttempt.objects.create(
            student=self.student, exam_paper=self.paper,
            attempt_mode='question_practice', total_marks_possible=300,
        )
        url = reverse('exam_papers:question_interface', args=[attempt.id, self.question.id])
        page = self.client.get(url + f'?part={self.other_part.id}')
        self.assertIsNone(page.context['focus_part'])


class TagPartTopicsTests(PartTopicsTestBase):
    """The classifier writes one topic per part, straight to the database."""

    def run_command(self, reply, *extra):
        """Drive the command with a canned reply and a canned scheme.

        The test paper has no PDFs, so without a stubbed scheme every question
        is skipped as "too little text to classify" before the model is asked.
        """
        out = StringIO()
        module = 'exam_papers.management.commands.tag_part_topics'
        with patch(f'{module}.ask_openai',
                   return_value=(json.dumps(reply), None)), \
             patch(f'{module}.part_scheme_text',
                   return_value='Differentiate and set equal to zero. 10 marks.'):
            call_command('tag_part_topics', self.paper.id, *extra, stdout=out)
        return out.getvalue()

    def reply_for(self, part, topic_name, confidence='high'):
        return {'parts': [{'id': part.id, 'topic': topic_name,
                           'confidence': confidence, 'reason': 'because'}]}

    def test_writes_one_topic_per_part(self):
        self.run_command(self.reply_for(self.part_a, 'Differential Calculus'))
        self.part_a.refresh_from_db()
        self.assertEqual(self.part_a.topic, self.calculus)

    def test_overwrites_a_topic_already_set(self):
        """Every part is retagged; corrections are made on the parts page."""
        self.run_command(self.reply_for(self.part_b, 'Finance'))
        self.part_b.refresh_from_db()
        self.assertEqual(self.part_b.topic, self.finance)

    def test_a_topic_that_does_not_exist_leaves_the_part_alone(self):
        output = self.run_command(self.reply_for(self.part_a, 'Vectors In Space'))
        self.part_a.refresh_from_db()
        self.assertEqual(self.part_a.topic, self.functions)
        self.assertIn('not a topic', output)
        self.assertIn('Vectors In Space', output)

    def test_dry_run_writes_nothing(self):
        output = self.run_command(
            self.reply_for(self.part_a, 'Differential Calculus'), '--dry-run')
        self.part_a.refresh_from_db()
        self.assertEqual(self.part_a.topic, self.functions)
        self.assertIn('Differential Calculus', output)
        self.assertIn('Nothing was written', output)

    def test_a_part_missing_from_the_reply_is_left_alone(self):
        output = self.run_command({'parts': []})
        self.part_a.refresh_from_db()
        self.assertEqual(self.part_a.topic, self.functions)
        self.assertIn('no reply for this part', output)

    def test_a_list_of_topics_is_reduced_to_its_first(self):
        reply = {'parts': [{'id': self.part_a.id,
                            'topic': ['Finance', 'Functions'],
                            'confidence': 'medium', 'reason': 'mortgage'}]}
        self.run_command(reply)
        self.part_a.refresh_from_db()
        self.assertEqual(self.part_a.topic, self.finance)


class RetagTests(PartTopicsTestBase):
    """Only a superuser may move a question or a part to another topic."""

    def part_url(self):
        return reverse('exam_papers:set_part_topic', args=[self.part_a.id])

    def test_a_superuser_can_retag_a_part(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.part_url(), {'topic': self.finance.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['topic'], 'Finance')
        self.part_a.refresh_from_db()
        self.assertEqual(self.part_a.topic, self.finance)

    def test_a_staff_teacher_cannot(self):
        """is_staff is every teacher; a topic is shared across all of them."""
        self.client.force_login(self.staff)
        response = self.client.post(self.part_url(), {'topic': self.finance.id})

        self.assertEqual(response.status_code, 403)
        self.part_a.refresh_from_db()
        self.assertEqual(self.part_a.topic, self.functions)

    def test_a_student_cannot(self):
        self.client.force_login(self.student)
        self.assertEqual(
            self.client.post(self.part_url(), {'topic': self.finance.id}).status_code,
            403)

    def test_a_blank_topic_clears_it(self):
        self.client.force_login(self.admin)
        self.client.post(self.part_url(), {'topic': ''})
        self.part_a.refresh_from_db()
        self.assertIsNone(self.part_a.topic)

    def test_a_topic_from_another_subject_is_refused(self):
        """A Maths part has no business under a Physics topic."""
        physics = Subject.objects.get(slug='physics')
        elsewhere = Topic.objects.create(name='Waves', subject=physics, paper='p1')

        self.client.force_login(self.admin)
        response = self.client.post(self.part_url(), {'topic': elsewhere.id})

        self.assertEqual(response.status_code, 400)
        self.part_a.refresh_from_db()
        self.assertEqual(self.part_a.topic, self.functions)

    def test_a_question_can_be_retagged_too(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse('exam_papers:set_question_topic', args=[self.question.id]),
            {'topic': self.finance.id})
        self.question.refresh_from_db()
        self.assertEqual(self.question.topic, self.finance)


class PartsPageTests(PartTopicsTestBase):
    url = reverse('exam_papers:parts_generator')

    def test_lists_only_parts_on_the_chosen_topic(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url, {'topic': self.calculus.id})
        self.assertEqual(response.context['groups'],
                         [(self.question, [self.part_b])])
        self.assertEqual(response.context['part_count'], 1)

    def test_parts_of_one_question_share_a_single_card(self):
        """The question image is shown once, not once per part."""
        self.part_a.topic = self.calculus
        self.part_a.save(update_fields=['topic'])

        self.client.force_login(self.admin)
        response = self.client.get(self.url, {'topic': self.calculus.id})

        self.assertEqual(response.context['groups'],
                         [(self.question, [self.part_a, self.part_b])])
        self.assertEqual(response.context['part_count'], 2)
        self.assertEqual(response.content.decode().count('data-question'), 1)

    def test_the_dropdown_is_for_superusers_only(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.url, {'topic': self.calculus.id}),
                            'topic-retag')

        self.client.force_login(self.staff)
        self.assertNotContains(self.client.get(self.url, {'topic': self.calculus.id}),
                               'topic-retag')

    def test_the_topic_map_is_gone(self):
        with self.assertRaises(NoReverseMatch):
            reverse('exam_papers:topic_cross_reference')


class AlgebraRuleTests(PartTopicsTestBase):
    def test_names_come_from_the_database_not_the_prompt(self):
        from exam_papers.management.commands.suggest_question_topics import algebra_rule
        general = Topic.objects.create(
            name='Algebra - Fractions Binomial,Long Division...', slug='algebra', subject=self.maths)
        inequalities = Topic.objects.create(
            name='Algebra-Simultaneous Equations_Inequalities...',
            slug='algebra-inequalities-and-factorisation', subject=self.maths)

        rule = algebra_rule([self.functions, general, inequalities], 'part')
        self.assertIn(f'"{inequalities.name}"', rule)
        self.assertIn(f'"{general.name}"', rule)
        self.assertNotIn('Algebra (1)', rule)

    def test_rule_is_dropped_when_there_is_no_inequalities_topic(self):
        from exam_papers.management.commands.suggest_question_topics import algebra_rule
        self.assertEqual(algebra_rule([self.functions]), '')


class PractiseQuestionLinkTests(PartTopicsTestBase):
    """Homework and study plans hand out a whole question by link, so one has
    to open that question and nothing else."""

    def setUp(self):
        self.client.force_login(self.student)

    def test_it_opens_the_question_interface_for_that_question(self):
        response = self.client.get(
            reverse('exam_papers:practise_question', args=[self.question.id]))
        self.assertEqual(response.status_code, 302)
        page = self.client.get(response['Location'])
        self.assertEqual(page.context['question'], self.question)
        self.assertIsNone(page.context['focus_part'])

    def test_it_reuses_the_students_practice_attempt(self):
        first = self.client.get(
            reverse('exam_papers:practise_question', args=[self.question.id]))
        second = self.client.get(
            reverse('exam_papers:practise_question', args=[self.other_question.id]))
        self.assertEqual(first['Location'].split('/')[3],
                         second['Location'].split('/')[3])

    def test_an_unpublished_paper_is_a_404(self):
        self.paper.is_published = False
        self.paper.save(update_fields=['is_published'])
        response = self.client.get(
            reverse('exam_papers:practise_question', args=[self.question.id]))
        self.assertEqual(response.status_code, 404)
