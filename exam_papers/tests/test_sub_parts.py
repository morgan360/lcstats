"""A part covering (i) and (ii) gets an answer box for each."""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import Subject
from exam_papers.models import (ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionAttempt,
                                ExamQuestionPart)

PAPER = {(2, 'a'): ['i', 'ii']}


class SubPartsTests(TestCase):
    def setUp(self):
        maths, _ = Subject.objects.get_or_create(slug='maths', defaults={'name': 'Maths'})
        self.paper = ExamPaper.objects.create(subject=maths, year=2025, paper_type='p1',
                                              total_marks=300, is_published=True,
                                              source_pdf='papers/2025.pdf')
        self.question = ExamQuestion.objects.create(exam_paper=self.paper, question_number=2,
                                                    total_marks=25)
        self.a = ExamQuestionPart.objects.create(question=self.question, label='(a)',
                                                 max_marks=15, order=1)
        self.b = ExamQuestionPart.objects.create(question=self.question, label='(b)',
                                                 max_marks=10, order=2)
        self.student = User.objects.create_user('niamh', password='pw')

    def fill(self, *args, paper=PAPER):
        with patch('exam_papers.management.commands.fill_sub_parts.question_sub_parts',
                   return_value=paper), \
             patch('django.db.models.fields.files.FieldFile.path', 'x.pdf'):
            call_command('fill_sub_parts', *args, stdout=open('/dev/null', 'w'))
        self.a.refresh_from_db()
        self.b.refresh_from_db()

    def open_question(self):
        self.client.force_login(self.student)
        return self.client.get(
            reverse('exam_papers:practise_question', args=[self.question.id]), follow=True)

    def test_the_paper_names_the_sub_parts(self):
        self.fill('--apply')

        self.assertEqual(self.a.sub_parts, 'i,ii')
        self.assertEqual(self.b.sub_parts, '')

    def test_a_broken_run_is_not_saved(self):
        # (i) lost from the text layer: better one box than the wrong ones
        self.fill('--apply', paper={(2, 'a'): ['ii', 'iii']})

        self.assertEqual(self.a.sub_parts, '')

    def test_a_report_writes_nothing(self):
        self.fill()

        self.assertEqual(self.a.sub_parts, '')

    def test_a_value_set_by_hand_is_kept_unless_overwriting(self):
        ExamQuestionPart.objects.filter(id=self.a.id).update(sub_parts='i,ii,iii')

        self.fill('--apply')
        self.assertEqual(self.a.sub_parts, 'i,ii,iii')

        self.fill('--apply', '--overwrite')
        self.assertEqual(self.a.sub_parts, 'i,ii')

    def test_display_reads_like_the_paper(self):
        self.assertEqual(ExamQuestionPart(sub_parts='i,ii').sub_parts_display, '(i) and (ii)')
        self.assertEqual(ExamQuestionPart(sub_parts='i,ii,iii').sub_parts_display,
                         '(i), (ii) and (iii)')
        self.assertEqual(ExamQuestionPart(sub_parts='').sub_parts_display, '')
        self.assertEqual(ExamQuestionPart(sub_parts='i').sub_parts_display, '')

    def test_a_part_with_sub_parts_gets_a_box_for_each(self):
        ExamQuestionPart.objects.filter(id=self.a.id).update(sub_parts='i,ii')

        response = self.open_question()

        self.assertContains(response, f'id="answer-{self.a.id}-i"')
        self.assertContains(response, f'id="answer-{self.a.id}-ii"')
        self.assertNotContains(response, f'id="answer-{self.a.id}"')
        # A plain letter keeps its one box
        self.assertContains(response, f'id="answer-{self.b.id}"')

    def test_the_last_answer_goes_back_into_its_boxes(self):
        ExamQuestionPart.objects.filter(id=self.a.id).update(sub_parts='i,ii')
        attempt = ExamAttempt.objects.create(student=self.student, exam_paper=self.paper)
        ExamQuestionAttempt.objects.create(
            exam_attempt=attempt, question_part=self.a, max_marks=15,
            student_answer=r'\text{(i) }2x+4\cos(4x)\quad \text{(ii) }y=4x+6')

        response = self.open_question()

        boxes = dict(next(p for p in response.context['parts_with_attempts']
                          if p['part'].id == self.a.id)['sub_part_boxes'])
        self.assertEqual(boxes, {'i': r'2x+4\cos(4x)', 'ii': 'y=4x+6'})

    def test_an_answer_from_before_the_boxes_goes_in_the_first(self):
        part = ExamQuestionPart(sub_parts='i,ii')

        self.assertEqual(part.split_answer('2x+4\\cos(4x)'), {'i': '2x+4\\cos(4x)'})

    def test_one_sub_part_left_out_is_left_out_of_the_split(self):
        part = ExamQuestionPart(sub_parts='i,ii')

        self.assertEqual(part.split_answer(r'\text{(ii) }y=4x+6'), {'ii': 'y=4x+6'})
