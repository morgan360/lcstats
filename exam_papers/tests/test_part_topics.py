"""Part-level topics: a question shows on every topic one of its parts is filed
under, a single part can be opened on its own, and a reviewed proposal file
never quietly overwrites tags set by hand."""
import importlib
import json
import tempfile
from io import StringIO
from pathlib import Path

from django.apps import apps
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

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
        cls.part_a.topics.set([cls.functions])
        cls.part_b.topics.set([cls.calculus, cls.functions])

        cls.other_question = ExamQuestion.objects.create(
            exam_paper=cls.paper, question_number=7, topic=cls.finance, total_marks=30,
        )
        cls.other_part = ExamQuestionPart.objects.create(
            question=cls.other_question, label='(a)', max_marks=30, order=1)

        cls.student = User.objects.create_user('student', password='pw')
        cls.staff = User.objects.create_user('teacher', password='pw', is_staff=True)


class SeedMigrationTests(PartTopicsTestBase):
    def test_copies_question_topic_to_untagged_parts_only(self):
        migration = importlib.import_module(
            'exam_papers.migrations.0021_examquestionpart_topics')
        self.other_part.topics.clear()

        migration.copy_question_topic_to_parts(apps, None)
        migration.copy_question_topic_to_parts(apps, None)  # safe to re-run

        self.assertEqual(list(self.other_part.topics.all()), [self.finance])
        self.assertEqual(set(self.part_b.topics.all()), {self.calculus, self.functions})


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

    def test_question_is_listed_once_despite_several_matching_parts(self):
        response = self.page(self.functions)
        self.assertEqual(response.context['total_questions'], 1)
        self.assertEqual(response.context['total_parts'], 2)


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


class ApplyProposalTests(PartTopicsTestBase):
    def apply(self, rows, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'proposal.json'
            path.write_text(json.dumps({'paper_id': self.paper.id, 'parts': rows}))
            out = StringIO()
            call_command('suggest_part_topics', '--apply', str(path), *extra, stdout=out)
            return out.getvalue()

    def row(self, part, topics, confidence='high'):
        return {'part_id': part.id, 'question': part.question.question_number,
                'label': part.label, 'topics': topics, 'confidence': confidence}

    def test_replaces_seeded_topic(self):
        # part_a holds only its question's topic, as the migration left it
        self.apply([self.row(self.part_a, ['Differential Calculus', 'functions'])])
        self.assertEqual(set(self.part_a.topics.all()), {self.calculus, self.functions})

    def test_keeps_hand_tagged_part_unless_overwrite(self):
        self.apply([self.row(self.part_b, ['Finance'])])
        self.assertEqual(set(self.part_b.topics.all()), {self.calculus, self.functions})

        self.apply([self.row(self.part_b, ['Finance'])], '--overwrite')
        self.assertEqual(list(self.part_b.topics.all()), [self.finance])

    def test_unknown_topic_saves_nothing_for_that_part(self):
        output = self.apply([self.row(self.part_a, ['Differential Calculus', 'Calculus-ish'])])
        self.assertIn('Calculus-ish', output)
        self.assertEqual(list(self.part_a.topics.all()), [self.functions])

    def test_below_confidence_floor_is_left_alone(self):
        self.apply([self.row(self.part_a, ['Finance'], confidence='low')])
        self.assertEqual(list(self.part_a.topics.all()), [self.functions])

    def test_part_from_another_paper_is_rejected(self):
        other = ExamPaper.objects.create(subject=self.maths, year=2020, paper_type='p1', total_marks=300)
        q = ExamQuestion.objects.create(exam_paper=other, question_number=1, total_marks=30)
        stray = ExamQuestionPart.objects.create(question=q, label='(a)', max_marks=30)
        output = self.apply([self.row(stray, ['Finance'])])
        self.assertIn('not a part of', output)
        self.assertFalse(stray.topics.exists())


class CrossReferenceTests(PartTopicsTestBase):
    url = reverse('exam_papers:topic_cross_reference')

    def test_staff_only(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_part_lands_in_each_of_its_topic_rows(self):
        self.other_part.topics.clear()
        self.client.force_login(self.staff)
        response = self.client.get(self.url)

        table = response.context['tables'][0]
        column = table['papers'].index(self.paper)
        cells = {(row['topic'].name if row['topic'] else None): row['cells'][column]['parts']
                 for row in table['rows']}
        self.assertEqual(cells['Differential Calculus'], [self.part_b])
        self.assertEqual(cells['Functions'], [self.part_a, self.part_b])
        self.assertEqual(cells[None], [self.other_part])
        self.assertContains(response, 'Q6(b)')
