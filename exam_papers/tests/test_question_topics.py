"""Question topics: a question lists under its main topic and, when ticked,
its secondary one; its need-to-know topic shows but never lists it. Parts keep
a topic of their own for the classifier, and a part can still be opened alone.
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

    def set_topics(self, **fields):
        ExamQuestion.objects.filter(pk=self.question.pk).update(**fields)

    def test_listed_under_its_main_topic(self):
        self.assertContains(self.page(self.functions), 'Question 6')

    def test_a_part_tag_alone_no_longer_lists_it(self):
        self.assertNotContains(self.page(self.calculus), 'Question 6')

    def test_a_ticked_secondary_topic_lists_it(self):
        self.set_topics(secondary_topic=self.calculus, list_under_secondary=True)
        self.assertContains(self.page(self.calculus), 'Question 6')

    def test_an_unticked_secondary_topic_does_not(self):
        self.set_topics(secondary_topic=self.calculus, list_under_secondary=False)
        self.assertNotContains(self.page(self.calculus), 'Question 6')

    def test_need_to_know_never_lists_it(self):
        self.set_topics(need_to_know_topic=self.finance)
        response = self.page(self.finance)
        self.assertContains(response, 'Question 7')
        self.assertNotContains(response, 'Question 6')

    def test_all_three_topics_are_shown_on_the_card(self):
        self.set_topics(secondary_topic=self.calculus, need_to_know_topic=self.finance)
        response = self.page(self.functions)
        self.assertContains(response, 'Also covers')
        self.assertContains(response, 'Need to know')
        self.assertContains(response, 'Differential Calculus')


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
    """Only a superuser may set a question's topics."""

    def url(self):
        return reverse('exam_papers:set_question_topics', args=[self.question.id])

    def post(self, user, **data):
        self.client.force_login(user)
        body = {'topic': self.functions.id, 'secondary_topic': '',
                'need_to_know_topic': '', 'list_under_secondary': ''}
        body.update(data)
        return self.client.post(self.url(), body)

    def test_a_superuser_can_set_all_three(self):
        response = self.post(self.admin, secondary_topic=self.calculus.id,
                             list_under_secondary='1',
                             need_to_know_topic=self.finance.id)
        self.assertEqual(response.status_code, 200)
        self.question.refresh_from_db()
        self.assertEqual(self.question.topic, self.functions)
        self.assertEqual(self.question.secondary_topic, self.calculus)
        self.assertTrue(self.question.list_under_secondary)
        self.assertEqual(self.question.need_to_know_topic, self.finance)

    def test_a_staff_teacher_cannot(self):
        """is_staff is every teacher; a topic is shared across all of them."""
        response = self.post(self.staff, topic=self.finance.id)
        self.assertEqual(response.status_code, 403)
        self.question.refresh_from_db()
        self.assertEqual(self.question.topic, self.functions)

    def test_a_student_cannot(self):
        self.assertEqual(self.post(self.student, topic=self.finance.id).status_code, 403)

    def test_the_tick_is_dropped_without_a_secondary(self):
        self.post(self.admin, list_under_secondary='1')
        self.question.refresh_from_db()
        self.assertIsNone(self.question.secondary_topic)
        self.assertFalse(self.question.list_under_secondary)

    def test_one_topic_cannot_fill_two_slots(self):
        response = self.post(self.admin, secondary_topic=self.functions.id)
        self.assertEqual(response.status_code, 400)
        self.question.refresh_from_db()
        self.assertIsNone(self.question.secondary_topic)

    def test_a_topic_from_another_subject_is_refused(self):
        """A Maths question has no business under a Physics topic."""
        physics = Subject.objects.get(slug='physics')
        elsewhere = Topic.objects.create(name='Waves', subject=physics, paper='p1')
        response = self.post(self.admin, need_to_know_topic=elsewhere.id)
        self.assertEqual(response.status_code, 400)
        self.question.refresh_from_db()
        self.assertIsNone(self.question.need_to_know_topic)

    def test_the_parts_pages_are_gone(self):
        for name in ('parts_generator', 'set_part_topic', 'set_question_topic',
                     'topic_cross_reference'):
            with self.assertRaises(NoReverseMatch):
                reverse(f'exam_papers:{name}')


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


class QuestionWorksheetTests(PartTopicsTestBase):
    """The worksheet lists questions by the same rule as the topic pages."""

    def setUp(self):
        self.client.force_login(self.student)
        ExamQuestion.objects.filter(pk=self.question.pk).update(image='q6.png')

    def listed(self, topic):
        response = self.client.get(reverse('exam_papers:worksheet_generator'),
                                   {'topic': topic.id})
        return list(response.context['questions']), list(response.context['topics'])

    def test_listed_under_its_main_topic(self):
        questions, topics = self.listed(self.functions)
        self.assertEqual(questions, [self.question])
        self.assertIn(self.functions, topics)

    def test_not_listed_under_a_topic_only_a_part_is_on(self):
        questions, topics = self.listed(self.calculus)
        self.assertEqual(questions, [])
        self.assertNotIn(self.calculus, topics)

    def test_listed_under_a_ticked_secondary(self):
        ExamQuestion.objects.filter(pk=self.question.pk).update(
            secondary_topic=self.calculus, list_under_secondary=True)
        questions, topics = self.listed(self.calculus)
        self.assertEqual(questions, [self.question])
        self.assertIn(self.calculus, topics)

    def test_the_topic_editor_is_for_superusers_only(self):
        url = reverse('exam_papers:worksheet_generator')
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(url, {'topic': self.functions.id}),
                            'topic-retag')
        self.client.force_login(self.staff)
        self.assertNotContains(self.client.get(url, {'topic': self.functions.id}),
                               'topic-retag')


class TagQuestionTopicsTests(PartTopicsTestBase):
    """The command ranks a question's topics by the part marks they carry."""

    def test_runner_up_and_third_fill_secondary_and_need_to_know(self):
        ExamQuestionPart.objects.create(
            question=self.question, label='(c)', max_marks=5, order=3,
            topic=self.finance)
        call_command('tag_question_topics', stdout=StringIO())
        self.question.refresh_from_db()
        # (b) Calculus carries 20 marks, (a) Functions 10, (c) Finance 5.
        self.assertEqual(self.question.topic, self.functions)  # already set, kept
        self.assertEqual(self.question.secondary_topic, self.calculus)
        self.assertTrue(self.question.list_under_secondary)
        self.assertEqual(self.question.need_to_know_topic, self.finance)

    def test_overwrite_reorders_by_marks(self):
        call_command('tag_question_topics', '--overwrite', stdout=StringIO())
        self.question.refresh_from_db()
        self.assertEqual(self.question.topic, self.calculus)
        self.assertEqual(self.question.secondary_topic, self.functions)
        self.assertTrue(self.question.list_under_secondary)  # 10 of 30 is a third

    def test_a_small_secondary_is_not_ticked(self):
        self.part_a.max_marks = 5
        self.part_a.topic = self.finance
        self.part_a.save()
        self.part_b.max_marks = 10
        self.part_b.save()
        ExamQuestionPart.objects.create(
            question=self.question, label='(c)', max_marks=25, order=3,
            topic=self.functions)
        ExamQuestion.objects.filter(pk=self.question.pk).update(topic=None)
        call_command('tag_question_topics', stdout=StringIO())
        self.question.refresh_from_db()
        # Functions 25, Calculus 10, Finance 5 of 40: Calculus is a quarter.
        self.assertEqual(self.question.topic, self.functions)
        self.assertEqual(self.question.secondary_topic, self.calculus)
        self.assertFalse(self.question.list_under_secondary)
        self.assertEqual(self.question.need_to_know_topic, self.finance)


class ExamQuestionsIndexTests(PartTopicsTestBase):
    """The Exam Questions page lists topics under Paper 1 and Paper 2."""

    def test_topics_are_grouped_by_paper(self):
        probability = Topic.objects.create(name='Probability', subject=self.maths, paper='p2')
        self.client.force_login(self.student)
        response = self.client.get(reverse('exam_papers:exam_questions_index'))
        groups = {g['label']: [r['topic'] for r in g['rows']]
                  for g in response.context['groups']}
        self.assertIn(self.functions, groups['Paper 1'])
        self.assertIn(probability, groups['Paper 2'])
        self.assertContains(response, '>Paper 1</h2>')
        self.assertContains(response, '>Paper 2</h2>')
