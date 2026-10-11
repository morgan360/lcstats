"""Marking scanned scripts of a teacher's exam: access, page matching, the
marker's proposed marks, and the teacher's overrides."""
import io
import json
import tempfile
from types import SimpleNamespace
from unittest import mock

import fitz
from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from openai import APITimeoutError
from PIL import Image, ImageDraw

from core.models import Subject
from exam_papers.models import (
    ExamPaper, ExamQuestion, ExamQuestionPart, ExamScript, ExamScriptMark, ExamScriptQuestion,
    TeacherExam, TeacherExamQuestion,
)
from exam_papers.services import script_marking
from exam_papers.services.exam_pdf import build_exam_pdf, exam_layout
from homework.models import TeacherClass, TeacherProfile
from interactive_lessons.models import Topic


def png(height=1200):
    img = Image.new('RGB', (1240, height), 'white')
    ImageDraw.Draw(img).rectangle((90, 80, 1100, 120), fill='black')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return ContentFile(buffer.getvalue(), name='q.png')


def pdf_of(pages):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page().insert_text((72, 72), 'answer', fontsize=12)
    return doc.tobytes()


def reply(parts):
    """A fake vision response carrying these parts."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({'parts': parts})))],
        usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=300))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), PRIVATE_MEDIA_ROOT=tempfile.mkdtemp())
class ExamMarkingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maths = Subject.objects.get(slug='maths')
        topic = Topic.objects.create(name='Probability X', subject=maths, paper='p2')
        paper = ExamPaper.objects.create(subject=maths, year=2023, paper_type='p2',
                                         total_marks=300, is_published=True)
        # Q1: parts with marks and schemes, (c) left out of the exam.
        cls.q1 = ExamQuestion.objects.create(exam_paper=paper, question_number=10, topic=topic,
                                             total_marks=50, image=png())
        cls.a = ExamQuestionPart.objects.create(question=cls.q1, label='(a)', max_marks=25, order=1,
                                                solution_image=png(400))
        cls.b = ExamQuestionPart.objects.create(question=cls.q1, label='(b)', max_marks=15, order=2,
                                                solution_image=png(400))
        cls.c = ExamQuestionPart.objects.create(question=cls.q1, label='(c)', max_marks=10, order=3,
                                                solution_image=png(400))
        # Q2: the parts' marks were never filled in, and there is no scheme.
        cls.q2 = ExamQuestion.objects.create(exam_paper=paper, question_number=2, topic=topic,
                                             total_marks=25, image=png())
        ExamQuestionPart.objects.create(question=cls.q2, label='(a)', order=1)
        ExamQuestionPart.objects.create(question=cls.q2, label='(b)', order=2)

        teachers = Group.objects.get(name='Teachers')
        cls.teacher = User.objects.create_user('teach', password='pw', is_staff=True)
        cls.teacher.groups.add(teachers)
        profile, _ = TeacherProfile.objects.get_or_create(user=cls.teacher)
        cls.student = User.objects.create_user('aoife', password='pw', first_name='Aoife', last_name='Byrne')
        cls.outsider = User.objects.create_user('notmine', password='pw')
        TeacherClass.objects.create(teacher=profile, name='6th Year').students.add(cls.student)
        cls.other_teacher = User.objects.create_user('teach2', password='pw', is_staff=True)
        cls.other_teacher.groups.add(teachers)

        cls.exam = TeacherExam.objects.create(owner=cls.teacher, subject=maths, title='Mid Term')
        cls.item1 = TeacherExamQuestion.objects.create(exam=cls.exam, question=cls.q1, order=0)
        cls.item1.omitted_parts.add(cls.c)
        cls.item2 = TeacherExamQuestion.objects.create(exam=cls.exam, question=cls.q2, order=1)

    def setUp(self):
        self.client.force_login(self.teacher)

    def upload(self, pages=None, student=None):
        pages = pages if pages is not None else max(last for _, last in exam_layout(self.exam).values())
        scan = ContentFile(pdf_of(pages), name='script.pdf')
        return self.client.post(reverse('exam_papers:script_upload', args=[self.exam.pk]),
                                {'student': (student or self.student).pk, 'scan': scan})

    def script(self):
        return ExamScript.objects.get(exam=self.exam, student=self.student)

    # ---- upload and page matching ----
    def test_a_scan_with_the_exams_page_count_lines_up_question_by_question(self):
        self.upload()
        script = self.script()
        layout = exam_layout(self.exam)
        self.assertTrue(script.pages_line_up)
        for question in script.questions.all():
            self.assertEqual((question.first_page, question.last_page), layout[question.item_id])
        # Q1 marked per part, without the left-out (c); Q2 as a whole question.
        q1, q2 = script.ordered_questions()
        self.assertEqual([(m.label, m.max_marks) for m in q1.marks.all()], [('(a)', 25), ('(b)', 15)])
        self.assertEqual([(m.label, m.max_marks, m.part) for m in q2.marks.all()],
                         [('Whole question', 25, None)])
        self.assertEqual(script.total, (None, 65))

    def test_a_scan_with_the_wrong_page_count_leaves_the_pages_to_the_teacher(self):
        response = self.upload(pages=2)
        script = self.script()
        self.assertFalse(script.pages_line_up)
        self.assertFalse(script.questions.exclude(first_page=None).exists())
        self.assertRedirects(response, reverse('exam_papers:script_detail', args=[self.exam.pk, script.pk]),
                             fetch_redirect_response=False)

    def test_only_students_from_the_teachers_own_classes(self):
        self.upload(student=self.outsider)
        self.assertFalse(ExamScript.objects.exists())

    # ---- access ----
    def test_another_teacher_cannot_see_the_script_or_its_pages(self):
        self.upload()
        script = self.script()
        self.client.force_login(self.other_teacher)
        for url in (reverse('exam_papers:marking_overview', args=[self.exam.pk]),
                    reverse('exam_papers:script_detail', args=[self.exam.pk, script.pk]),
                    reverse('exam_papers:script_page', args=[self.exam.pk, script.pk, 1]),
                    reverse('exam_papers:results_sheet', args=[self.exam.pk, script.pk])):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_students_are_kept_out(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('exam_papers:marking_overview',
                                                 args=[self.exam.pk])).status_code, 403)

    def test_the_owner_gets_the_page_images(self):
        self.upload()
        response = self.client.get(reverse('exam_papers:script_page', args=[self.exam.pk, self.script().pk, 2]))
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    # ---- the marker ----
    def mark_all(self, fake):
        with mock.patch.object(script_marking, '_vision_completion', side_effect=fake) as call:
            url = reverse('exam_papers:script_mark_next', args=[self.exam.pk, self.script().pk])
            for _ in range(5):
                data = self.client.post(url).json()
                if not data['success'] or data['complete']:
                    break
        return data, call

    def test_marks_come_back_per_part_and_doubtful_ones_are_left_for_the_teacher(self):
        self.upload()
        data, call = self.mark_all(lambda **kw: reply([
            {'label': '(a)', 'readable': True, 'has_working': True, 'confidence': 'high',
             'estimated_mark': 20, 'transcription': '$P = 0.3$', 'mark_reasoning': 'High partial',
             'feedback': 'Good start.'},
            {'label': '(b)', 'readable': True, 'has_working': True, 'confidence': 'low',
             'estimated_mark': 12, 'feedback': 'Hard to read.'},
        ]))
        self.assertTrue(data['complete'])
        self.assertEqual(call.call_count, 1)  # Q2 has no scheme, so is never sent
        q1, q2 = self.script().ordered_questions()
        a, b = q1.marks.all()
        self.assertEqual((a.ai_mark, a.feedback, a.transcription), (20, 'Good start.', '$P = 0.3$'))
        self.assertIsNone(b.ai_mark)  # low confidence: no mark
        self.assertEqual(q2.status, ExamScriptQuestion.MARKED)
        self.assertIsNone(q2.marks.get().ai_mark)
        # The left-out part is not asked about, and the students' note is passed on.
        prompt = call.call_args.kwargs['messages'][0]['content'][0]['text']
        self.assertIn('(a): 25 marks', prompt)
        self.assertNotIn('(c): 10 marks', prompt)
        self.assertIn('Do not answer part (c).', prompt)

    def test_a_blank_part_scores_zero_and_an_impossible_mark_is_refused(self):
        self.upload()
        self.mark_all(lambda **kw: reply([
            {'label': '(a)', 'readable': True, 'has_working': False, 'confidence': 'high', 'estimated_mark': 0},
            {'label': '(b)', 'readable': True, 'has_working': True, 'confidence': 'high', 'estimated_mark': 40},
        ]))
        a, b = self.script().ordered_questions()[0].marks.all()
        self.assertEqual(a.ai_mark, 0)
        self.assertIsNone(b.ai_mark)

    def test_a_timeout_keeps_the_question_pending(self):
        self.upload()

        def timeout(**kw):
            raise APITimeoutError(request=mock.Mock())
        data, _ = self.mark_all(timeout)
        self.assertFalse(data['success'])
        self.assertIn('Mark again', data['message'])
        self.assertEqual(self.script().ordered_questions()[0].status, ExamScriptQuestion.PENDING)

    def test_an_unusable_reply_fails_the_question_without_inventing_marks(self):
        self.upload()
        self.mark_all(lambda **kw: SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='not json'))], usage=None))
        q1 = self.script().ordered_questions()[0]
        self.assertEqual(q1.status, ExamScriptQuestion.FAILED)
        self.assertFalse(q1.marks.exclude(ai_mark=None).exists())

    # ---- the teacher's review ----
    def save(self, **fields):
        return self.client.post(reverse('exam_papers:script_save', args=[self.exam.pk, self.script().pk]),
                                fields)

    def test_the_teachers_marks_win_and_make_the_total(self):
        self.upload()
        self.mark_all(lambda **kw: reply([
            {'label': '(a)', 'readable': True, 'has_working': True, 'confidence': 'high', 'estimated_mark': 20},
            {'label': '(b)', 'readable': True, 'has_working': True, 'confidence': 'high', 'estimated_mark': 10},
        ]))
        q1, q2 = self.script().ordered_questions()
        a, b = q1.marks.all()
        whole = q2.marks.get()
        self.save(**{f'mark_{a.pk}': '', f'mark_{b.pk}': '12', f'mark_{whole.pk}': '18',
                     'teacher_comment': 'Well done', 'reviewed': '1'})
        script = self.script()
        self.assertEqual(script.total, (20 + 12 + 18, 65))
        self.assertIsNotNone(script.reviewed_at)

        sheet = self.client.get(reverse('exam_papers:results_sheet', args=[self.exam.pk, script.pk]))
        self.assertContains(sheet, '50 / 65')
        self.assertContains(sheet, 'Aoife Byrne')
        csv = self.client.get(reverse('exam_papers:results_csv', args=[self.exam.pk])).content.decode()
        self.assertIn('Aoife Byrne,aoife,32,18,50,yes', csv)

    def test_a_mark_over_the_maximum_is_refused(self):
        self.upload()
        a = ExamScriptMark.objects.get(question__script=self.script(), label='(a)')
        self.save(**{f'mark_{a.pk}': '26'})
        a.refresh_from_db()
        self.assertIsNone(a.teacher_mark)

    def test_moving_a_questions_pages_sends_it_back_to_be_marked(self):
        self.upload()
        self.mark_all(lambda **kw: reply([
            {'label': '(a)', 'readable': True, 'has_working': True, 'confidence': 'high', 'estimated_mark': 20},
            {'label': '(b)', 'readable': True, 'has_working': True, 'confidence': 'high', 'estimated_mark': 10},
        ]))
        q1 = self.script().ordered_questions()[0]
        moved = str(q1.last_page + 1)  # one page on: a page that is in the scan
        self.save(**{f'first_{q1.pk}': moved, f'last_{q1.pk}': moved})
        q1.refresh_from_db()
        self.assertEqual(q1.status, ExamScriptQuestion.PENDING)
        self.assertFalse(q1.marks.exclude(ai_mark=None).exists())

    def test_the_exam_pdf_and_its_layout_agree(self):
        layout = exam_layout(self.exam)
        doc = fitz.open(stream=build_exam_pdf(self.exam), filetype='pdf')
        self.assertEqual(max(last for _, last in layout.values()), doc.page_count)
        first, _ = layout[self.item2.id]
        self.assertIn('Question 2', doc[first - 1].get_text())


class TidyMathsTests(TestCase):
    def test_a_lopsided_dollar_pair_is_made_inline(self):
        self.assertEqual(script_marking.tidy_maths(r"state '$$\sqrt{-7}$ is not real'"),
                         r"state '$\sqrt{-7}$ is not real'")

    def test_proper_maths_is_left_alone(self):
        for text in (r'$x = 2$ and $$y = 3$$', r'$a$, $b$', 'no maths'):
            self.assertEqual(script_marking.tidy_maths(text), text)
