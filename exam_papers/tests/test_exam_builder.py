"""Teachers' own exams: who may reach them, building one, and the two PDFs."""
import io
import tempfile

import fitz
from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image, ImageDraw

from core.models import Subject
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart, TeacherExam
from exam_papers.services.exam_pdf import (
    build_exam_pdf, build_exam_scheme_pdf, footer_cuts, printed_heading_bottom,
    without_page_footers, without_printed_heading, without_spare_last_page,
)
from interactive_lessons.models import Topic


def crop(with_heading=True, width=1240):
    """A fake question crop: an optional SEC-style heading line, then body text."""
    img = Image.new('RGB', (width, 1600), 'white')
    draw = ImageDraw.Draw(img)
    y = 80
    if with_heading:
        # "Question 6" at the left margin, "(30 marks)" at the right, nothing between.
        draw.rectangle((90, y, 300, y + 22), fill='black')
        draw.rectangle((width - 260, y, width - 90, y + 22), fill='black')
        y += 60
    for _ in range(12):  # lines of body text running most of the width
        draw.rectangle((90, y, width - 120, y + 18), fill='black')
        y += 40
    return img


def png(img=None):
    buffer = io.BytesIO()
    (img or crop()).save(buffer, format='PNG')
    return ContentFile(buffer.getvalue(), name='q.png')


class PrintedHeadingTests(TestCase):
    def test_the_heading_line_is_found_and_trimmed(self):
        img = crop()
        bottom = printed_heading_bottom(img)
        self.assertIsNotNone(bottom)
        self.assertTrue(100 <= bottom <= 110)
        self.assertEqual(without_printed_heading(img).height, img.height - bottom)

    def test_a_crop_without_one_is_left_whole(self):
        # 2012 Paper 1 style: the first line is question text, not a heading.
        img = crop(with_heading=False)
        self.assertIsNone(printed_heading_bottom(img))
        self.assertIs(without_printed_heading(img), img)


def pages(count, last_page=None, width=1240):
    """Whole A4 pages like the SEC crops: a grid down most of each page, then the
    two-line footer ("Leaving Certificate 2022 / Mathematics, Paper 1") at 0.95."""
    page_h = width * 297 / 210
    img = Image.new('RGB', (width, round(page_h * count)), 'white')
    draw = ImageDraw.Draw(img)
    for p in range(count):
        top = p * page_h
        if p == count - 1 and last_page == 'spare':
            # The 2012-2014 back page: one full-page grid, then the paper's title block.
            draw.rectangle((90, top + 0.05 * page_h, width - 90, top + 0.85 * page_h), outline='black', width=3)
            for k in range(3):
                draw.rectangle((90, top + (0.88 + 0.025 * k) * page_h, 700, top + (0.895 + 0.025 * k) * page_h), fill='black')
            continue
        # A line of question text, then its answer grid.
        draw.rectangle((90, top + 0.05 * page_h, width - 200, top + 0.06 * page_h), fill='black')
        draw.rectangle((90, top + 0.1 * page_h, width - 90, top + 0.85 * page_h), outline='black', width=3)
        if p == count - 1 and last_page == 'to_edge':
            # A diagram that runs down into the footer area: nothing to cut.
            draw.rectangle((90, top + 0.86 * page_h, width - 90, top + 0.99 * page_h), fill='black')
            continue
        for k in range(2):
            draw.rectangle((90, top + (0.95 + 0.015 * k) * page_h, 400, top + (0.958 + 0.015 * k) * page_h), fill='black')
    return img, page_h


class PageFooterTests(TestCase):
    def ink_rows(self, img, top, bottom):
        import numpy as np
        return int((np.asarray(img.convert('L'))[round(top):round(bottom)].min(axis=1) < 200).sum())

    def test_every_pages_footer_is_painted_out_and_the_grid_kept(self):
        img, page_h = pages(3)
        self.assertEqual(len(footer_cuts(img)), 3)
        clean = without_page_footers(img)
        for p in range(3):
            self.assertEqual(self.ink_rows(clean, (p + 0.9) * page_h, (p + 1) * page_h), 0)
            self.assertGreater(self.ink_rows(clean, (p + 0.1) * page_h, (p + 0.86) * page_h), 0)

    def test_a_page_with_ink_running_to_the_edge_is_left_alone(self):
        img, page_h = pages(2, last_page='to_edge')
        self.assertEqual(len(footer_cuts(img)), 1)  # only the first page's footer

    def test_a_crop_that_is_not_whole_pages_is_not_touched(self):
        img = crop()
        self.assertEqual(footer_cuts(img), [])
        self.assertIs(without_page_footers(img), img)

    def test_a_spare_back_page_is_dropped(self):
        img, page_h = pages(3, last_page='spare')
        self.assertAlmostEqual(without_spare_last_page(img).height, 2 * page_h, delta=1)

    def test_an_ordinary_last_page_is_kept(self):
        img, _ = pages(3)
        self.assertIs(without_spare_last_page(img), img)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ExamBuilderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.algebra = Topic.objects.create(name='Algebra X', subject=cls.maths, paper='p1')
        cls.trig = Topic.objects.create(name='Trig X', subject=cls.maths, paper='p2')
        cls.paper = ExamPaper.objects.create(subject=cls.maths, year=2019, paper_type='p1',
                                             total_marks=300, is_published=True)
        cls.q_alg = ExamQuestion.objects.create(exam_paper=cls.paper, question_number=6,
                                                topic=cls.algebra, total_marks=30, image=png())
        # total_marks never filled in: the marks live on the parts.
        cls.q_trig = ExamQuestion.objects.create(exam_paper=cls.paper, question_number=8,
                                                 topic=cls.trig, total_marks=0, image=png())
        ExamQuestionPart.objects.create(question=cls.q_trig, label='(a)', max_marks=15, order=1,
                                        solution_image=png(crop(with_heading=False)))
        ExamQuestionPart.objects.create(question=cls.q_trig, label='(b)', max_marks=10, order=2)

        teachers = Group.objects.get(name='Teachers')
        cls.teacher = User.objects.create_user('teach', password='pw', is_staff=True)
        cls.teacher.groups.add(teachers)
        cls.other_teacher = User.objects.create_user('teach2', password='pw', is_staff=True)
        cls.other_teacher.groups.add(teachers)
        cls.student = User.objects.create_user('stud', password='pw')

    def setUp(self):
        self.client.force_login(self.teacher)

    def make_exam(self, *questions, **details):
        response = self.client.post(reverse('exam_papers:exam_create'),
                                    {'title': details.pop('title', 'Mock Alpha')})
        exam = TeacherExam.objects.get(owner=self.teacher)
        for question in questions:
            self.client.post(reverse('exam_papers:exam_add_question', args=[exam.pk]),
                             {'question_id': question.pk})
        if details:
            TeacherExam.objects.filter(pk=exam.pk).update(**details)
            exam.refresh_from_db()
        self.assertRedirects(response, reverse('exam_papers:exam_builder', args=[exam.pk]),
                             fetch_redirect_response=False)
        return exam

    def order(self, exam):
        return [item.question_id for item in exam.ordered_items()]

    # ---- access ----
    def test_students_are_kept_out(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('exam_papers:my_exams')).status_code, 403)
        self.assertEqual(self.client.post(reverse('exam_papers:exam_create'),
                                          {'title': 'x'}).status_code, 403)

    def test_a_teacher_cannot_reach_another_teachers_exam(self):
        exam = self.make_exam(self.q_alg)
        self.client.force_login(self.other_teacher)
        for name in ('exam_builder', 'exam_pdf', 'exam_scheme_pdf'):
            self.assertEqual(self.client.get(reverse(f'exam_papers:{name}', args=[exam.pk])).status_code, 404)
        self.client.post(reverse('exam_papers:exam_delete', args=[exam.pk]))
        self.assertTrue(TeacherExam.objects.filter(pk=exam.pk).exists())
        self.assertNotContains(self.client.get(reverse('exam_papers:my_exams')), 'Mock Alpha')

    # ---- building ----
    def test_questions_from_two_topics_are_added_once_each_in_order(self):
        exam = self.make_exam(self.q_alg, self.q_trig, self.q_alg)
        self.assertEqual(self.order(exam), [self.q_alg.pk, self.q_trig.pk])
        self.assertEqual(exam.total_marks, 55)  # 30 + the trig parts' 15 + 10

    def test_moving_and_removing_keep_the_order_tidy(self):
        exam = self.make_exam(self.q_alg, self.q_trig)
        trig_item = exam.items.get(question=self.q_trig)
        self.client.post(reverse('exam_papers:exam_move_question', args=[exam.pk, trig_item.pk]),
                         {'direction': 'up'})
        self.assertEqual(self.order(exam), [self.q_trig.pk, self.q_alg.pk])

        self.client.post(reverse('exam_papers:exam_remove_question', args=[exam.pk, trig_item.pk]))
        self.assertEqual(self.order(exam), [self.q_alg.pk])
        self.assertEqual(list(exam.items.values_list('order', flat=True)), [0])

    def test_the_builder_lists_a_topics_questions_and_marks_those_added(self):
        exam = self.make_exam(self.q_alg)
        page = self.client.get(reverse('exam_papers:exam_builder', args=[exam.pk]),
                               {'topic': self.algebra.pk})
        self.assertContains(page, 'Added as Q1')
        page = self.client.get(reverse('exam_papers:exam_builder', args=[exam.pk]),
                               {'topic': self.trig.pk})
        self.assertContains(page, '+ Add to exam')
        self.assertContains(page, '25 marks')

    # ---- PDFs ----
    def test_the_exam_pdf_is_renumbered_with_a_cover_and_page_numbers(self):
        exam = self.make_exam(self.q_trig, self.q_alg, subtitle='6th Year HL', duration_minutes=90)
        doc = fitz.open(stream=build_exam_pdf(exam), filetype='pdf')
        self.assertEqual(doc.page_count, 3)  # cover + one page per question

        cover = doc[0].get_text()
        for expected in ('Mock Alpha', '6th Year HL', 'Time allowed: 1 h 30 min',
                         'Total marks: 55', 'Name:', 'Instructions'):
            self.assertIn(expected, cover)
        self.assertNotIn('Page 1 of', cover)

        first, second = doc[1].get_text(), doc[2].get_text()
        self.assertIn('Question 1', first)
        self.assertIn('(25 marks)', first)
        self.assertIn('Question 2', second)
        self.assertIn('(30 marks)', second)
        self.assertIn('Page 2 of 2', second)
        # The source is never on the students' copy.
        self.assertNotIn('2019', ''.join(page.get_text() for page in doc))

    def test_the_scheme_names_each_source_under_the_new_numbers(self):
        exam = self.make_exam(self.q_trig, self.q_alg)
        text = '\n'.join(page.get_text() for page in
                         fitz.open(stream=build_exam_scheme_pdf(exam), filetype='pdf'))
        self.assertIn('Question 1', text)
        self.assertIn('Source: 2019 Paper 1, Question 8', text)
        self.assertIn('Source: 2019 Paper 1, Question 6', text)
        self.assertIn('No marking scheme on file for this question.', text)  # q_alg has none

    def test_the_downloads_are_pdf_files(self):
        exam = self.make_exam(self.q_alg)
        for name in ('exam_pdf', 'exam_scheme_pdf'):
            response = self.client.get(reverse(f'exam_papers:{name}', args=[exam.pk]))
            self.assertEqual(response['Content-Type'], 'application/pdf')
            self.assertTrue(response.content.startswith(b'%PDF'))

    def test_an_empty_exam_has_nothing_to_download(self):
        exam = self.make_exam()
        response = self.client.get(reverse('exam_papers:exam_pdf', args=[exam.pk]))
        self.assertRedirects(response, reverse('exam_papers:exam_builder', args=[exam.pk]),
                             fetch_redirect_response=False)
