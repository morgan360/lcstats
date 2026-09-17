"""The PDF worksheet: what it contains, and that one missing file does not cost
the rest of the download."""
import io
import tempfile

import fitz
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from core.models import Subject
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart
from exam_papers.services.worksheet_pdf import build_worksheet_pdf
from interactive_lessons.models import Topic


def png(width=900, height=1200, colour=(240, 240, 240)):
    buffer = io.BytesIO()
    Image.new('RGB', (width, height), colour).save(buffer, format='PNG')
    return ContentFile(buffer.getvalue(), name='page.png')


# Saving through an ImageField writes a real file; a temporary root keeps the
# project's own media/ out of it.
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class WorksheetPdfTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(name='Integration', subject=cls.maths, paper='p1')
        cls.paper = ExamPaper.objects.create(
            subject=cls.maths, year=2019, paper_type='p1',
            total_marks=300, is_published=True,
        )
        cls.question = ExamQuestion.objects.create(
            exam_paper=cls.paper, question_number=6, topic=cls.topic, total_marks=30,
            image=png(),
        )
        cls.part = ExamQuestionPart.objects.create(
            question=cls.question, label='(a)', max_marks=10, order=1,
            solution_image=png(900, 400),
        )
        cls.part.topics.set([cls.topic])
        cls.student = User.objects.create_user('student', password='pw')

    def pdf(self, data):
        return fitz.open(stream=data, filetype='pdf')

    def test_question_heading_and_image_are_on_the_page(self):
        doc = self.pdf(build_worksheet_pdf([self.question], title='Integration'))
        text = doc[0].get_text()
        self.assertIn('Integration', text)
        self.assertIn('2019 Paper 1 - Question 6 (30 marks)', text)
        self.assertEqual(len(doc[0].get_images()), 1)

    def test_marking_schemes_are_added_only_when_asked_for(self):
        without = self.pdf(build_worksheet_pdf([self.question]))
        with_schemes = self.pdf(build_worksheet_pdf([self.question], include_solutions=True))

        self.assertNotIn('Marking scheme', without[0].get_text())
        joined = '\n'.join(page.get_text() for page in with_schemes)
        self.assertIn('Marking scheme', joined)
        self.assertIn('(a)', joined)

    def test_a_missing_image_costs_only_its_own_question(self):
        gone = ExamQuestion.objects.create(
            exam_paper=self.paper, question_number=7, topic=self.topic, total_marks=30,
            image='exam_papers/questions/not-here.png',
        )
        doc = self.pdf(build_worksheet_pdf([gone, self.question]))
        joined = '\n'.join(page.get_text() for page in doc)

        self.assertIn('No image of this question on file.', joined)
        self.assertIn('Question 6', joined)
        self.assertEqual(sum(len(page.get_images()) for page in doc), 1)

    def test_nothing_selected_still_gives_a_readable_pdf(self):
        doc = self.pdf(build_worksheet_pdf([]))
        self.assertEqual(doc.page_count, 1)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class WorksheetDownloadViewTests(WorksheetPdfTests):
    def setUp(self):
        self.client.force_login(self.student)

    def test_download_is_a_pdf_attachment_named_for_the_topic(self):
        response = self.client.post(reverse('exam_papers:worksheet_pdf'),
                                    {'question_ids': [self.question.id]})
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename="integration-exam-questions.pdf"',
                      response['Content-Disposition'])
        self.assertGreater(fitz.open(stream=response.content, filetype='pdf').page_count, 0)

    def test_no_selection_goes_back_to_the_generator(self):
        response = self.client.post(reverse('exam_papers:worksheet_pdf'), {})
        self.assertRedirects(response, reverse('exam_papers:worksheet_generator'))
