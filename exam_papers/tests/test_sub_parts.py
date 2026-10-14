"""A part covering (i) and (ii) says so beside its one answer box."""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import Subject
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart

SCHEME = {
    (2, 'a', None): {}, (2, 'a', 'ii'): {}, (2, 'a', 'i'): {},
    (2, 'b', None): {},
}


class SubPartsTests(TestCase):
    def setUp(self):
        maths, _ = Subject.objects.get_or_create(slug='maths', defaults={'name': 'Maths'})
        self.paper = ExamPaper.objects.create(subject=maths, year=2025, paper_type='p1',
                                              total_marks=300, is_published=True,
                                              marking_scheme_pdf='schemes/2025.pdf')
        self.question = ExamQuestion.objects.create(exam_paper=self.paper, question_number=2,
                                                    total_marks=25)
        self.a = ExamQuestionPart.objects.create(question=self.question, label='(a)',
                                                 max_marks=15, order=1)
        self.b = ExamQuestionPart.objects.create(question=self.question, label='(b)',
                                                 max_marks=10, order=2)

    def fill(self, *args):
        with patch('exam_papers.management.commands.fill_sub_parts.detect_marking_scheme_layout',
                   return_value=SCHEME), \
             patch('django.db.models.fields.files.FieldFile.path', 'x.pdf'):
            call_command('fill_sub_parts', *args, stdout=open('/dev/null', 'w'))
        self.a.refresh_from_db()
        self.b.refresh_from_db()

    def test_the_scheme_names_the_sub_parts_in_order(self):
        self.fill('--apply')

        self.assertEqual(self.a.sub_parts, 'i,ii')
        self.assertEqual(self.b.sub_parts, '')

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

    def test_the_question_page_tells_the_student_to_answer_every_sub_part(self):
        ExamQuestionPart.objects.filter(id=self.a.id).update(sub_parts='i,ii')
        self.client.force_login(User.objects.create_user('niamh', password='pw'))

        response = self.client.get(
            reverse('exam_papers:practise_question', args=[self.question.id]), follow=True)

        self.assertContains(response, 'This part has <strong>(i) and (ii)</strong>', count=1)
