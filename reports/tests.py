import json
from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from homework.models import TeacherClass, TeacherProfile
from interactive_lessons.models import Question, Topic
from quickkicks.models import QuickKick, QuickKickView
from students.models import QuestionAttempt, StudentProfile

from . import services
from .models import (
    ClassSession,
    ClassTest,
    CommentPreset,
    StudentClassNote,
    StudentSessionRecord,
    TestResult,
)


def make_teacher(username):
    user = User.objects.create_user(username=username, password='pw', is_staff=True)
    group, _ = Group.objects.get_or_create(name='Teachers')
    user.groups.add(group)
    profile = TeacherProfile.objects.create(user=user)
    return user, profile


class BaseReportTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher, cls.teacher_profile = make_teacher('teacher_a')
        cls.other_teacher, cls.other_profile = make_teacher('teacher_b')
        cls.student1 = User.objects.create_user(username='student1', password='pw', first_name='Aoife')
        cls.student2 = User.objects.create_user(username='student2', password='pw', first_name='Brian')
        cls.teacher_class = TeacherClass.objects.create(teacher=cls.teacher_profile, name='6th Year HL')
        cls.teacher_class.students.add(cls.student1, cls.student2)

    def login_teacher(self):
        self.client.login(username='teacher_a', password='pw')


class AccessControlTests(BaseReportTestCase):
    def test_non_teacher_gets_403(self):
        self.client.login(username='student1', password='pw')
        response = self.client.get(reverse('reports:daily_entry', args=[self.teacher_class.id]))
        self.assertEqual(response.status_code, 403)

    def test_other_teacher_blocked_from_class(self):
        self.client.login(username='teacher_b', password='pw')
        response = self.client.get(reverse('reports:daily_entry', args=[self.teacher_class.id]))
        self.assertEqual(response.status_code, 403)

    def test_other_teacher_blocked_from_set_record(self):
        self.login_teacher()
        self.client.get(reverse('reports:daily_entry', args=[self.teacher_class.id]))
        record = StudentSessionRecord.objects.first()

        self.client.login(username='teacher_b', password='pw')
        response = self.client.post(
            reverse('reports:set_record', args=[record.id]),
            data=json.dumps({'field': 'attendance', 'value': 'absent'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_other_teacher_blocked_from_student_report(self):
        self.client.login(username='teacher_b', password='pw')
        response = self.client.get(reverse('reports:student_report', args=[self.student1.id]))
        self.assertEqual(response.status_code, 403)


class DailyEntryTests(BaseReportTestCase):
    def test_creates_session_and_default_records_idempotently(self):
        self.login_teacher()
        url = reverse('reports:daily_entry', args=[self.teacher_class.id])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ClassSession.objects.count(), 1)
        session = ClassSession.objects.get()
        self.assertEqual(session.records.count(), 2)
        self.assertTrue(all(r.attendance == 'present' and r.homework == 'done' for r in session.records.all()))

        self.client.get(url)
        self.assertEqual(ClassSession.objects.count(), 1)
        self.assertEqual(StudentSessionRecord.objects.count(), 2)

    def test_set_record_persists_and_validates(self):
        self.login_teacher()
        self.client.get(reverse('reports:daily_entry', args=[self.teacher_class.id]))
        record = StudentSessionRecord.objects.get(student=self.student1)
        url = reverse('reports:set_record', args=[record.id])

        response = self.client.post(
            url, data=json.dumps({'field': 'attendance', 'value': 'late'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.attendance, 'late')

        response = self.client.post(
            url, data=json.dumps({'field': 'homework', 'value': 'nonsense'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_set_comment(self):
        self.login_teacher()
        self.client.get(reverse('reports:daily_entry', args=[self.teacher_class.id]))
        record = StudentSessionRecord.objects.get(student=self.student1)
        preset = CommentPreset.objects.filter(category='behaviour').first()

        response = self.client.post(
            reverse('reports:set_record', args=[record.id]),
            data=json.dumps({'field': 'comment', 'preset_id': preset.id, 'text': 'settled after'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.comment_preset, preset)
        self.assertEqual(record.comment_text, 'settled after')


class ClassTestTests(BaseReportTestCase):
    def test_create_and_upsert_results(self):
        self.login_teacher()
        response = self.client.post(
            reverse('reports:test_list', args=[self.teacher_class.id]),
            {'name': 'Algebra test', 'date': '2026-07-20', 'max_marks': '50'},
        )
        self.assertEqual(response.status_code, 302)
        test = ClassTest.objects.get()
        url = reverse('reports:test_detail', args=[test.id])

        response = self.client.post(url, {
            f'score_{self.student1.id}': '42.5',
            f'comment_{self.student1.id}': 'good',
            f'score_{self.student2.id}': '',
        })
        self.assertEqual(response.status_code, 302)
        result1 = TestResult.objects.get(test=test, student=self.student1)
        self.assertEqual(float(result1.score), 42.5)
        self.assertEqual(result1.percentage, 85.0)
        result2 = TestResult.objects.get(test=test, student=self.student2)
        self.assertIsNone(result2.score)

        # Upsert: resubmit changes the same rows
        self.client.post(url, {
            f'score_{self.student1.id}': '40',
            f'score_{self.student2.id}': '10',
        })
        self.assertEqual(TestResult.objects.filter(test=test).count(), 2)
        self.assertEqual(float(TestResult.objects.get(test=test, student=self.student1).score), 40.0)

    def test_score_over_max_rejected(self):
        self.login_teacher()
        test = ClassTest.objects.create(teacher_class=self.teacher_class, name='T', date=date(2026, 7, 20), max_marks=50)
        self.client.post(reverse('reports:test_detail', args=[test.id]), {
            f'score_{self.student1.id}': '80',
        })
        self.assertFalse(TestResult.objects.filter(test=test, student=self.student1).exists())


class ActivityServiceTests(BaseReportTestCase):
    def test_get_activity_by_day_counts_sources(self):
        profile = StudentProfile.objects.get(user=self.student1)
        topic = Topic.objects.create(name='Algebra')
        question = Question.objects.create(topic=topic)
        day = timezone.now() - timedelta(days=2)
        QuestionAttempt.objects.create(student=profile, question=question, student_answer='x', attempted_at=day)
        QuestionAttempt.objects.create(student=profile, question=question, student_answer='y', attempted_at=day)
        quickkick = QuickKick.objects.create(
            title='QK', topic=topic, content_type='geogebra', geogebra_code='abc123'
        )
        QuickKickView.objects.create(user=self.student1, quickkick=quickkick, viewed_at=day)

        start = timezone.now() - timedelta(days=7)
        end = timezone.now()
        with self.assertNumQueries(5):
            activity = services.get_activity_by_day([self.student1, self.student2], start, end)

        day_key = day.date()
        self.assertEqual(activity[self.student1.id][day_key]['questions'], 2)
        self.assertEqual(activity[self.student1.id][day_key]['quickkicks'], 1)
        self.assertEqual(activity[self.student1.id][day_key]['total'], 3)
        self.assertNotIn(self.student2.id, activity)

    def test_user_ids_active_since(self):
        profile = StudentProfile.objects.get(user=self.student1)
        topic = Topic.objects.create(name='Trig')
        question = Question.objects.create(topic=topic)
        QuestionAttempt.objects.create(student=profile, question=question, student_answer='x', attempted_at=timezone.now())
        active = services.user_ids_active_since(
            [self.student1, self.student2], timezone.now() - timedelta(days=1)
        )
        self.assertEqual(active, {self.student1.id})


class StudentReportTests(BaseReportTestCase):
    def test_report_renders_with_data(self):
        self.login_teacher()
        session = ClassSession.objects.create(teacher_class=self.teacher_class, date=timezone.localdate())
        StudentSessionRecord.objects.create(session=session, student=self.student1, attendance='late', homework='partial')
        test = ClassTest.objects.create(teacher_class=self.teacher_class, name='T', date=timezone.localdate(), max_marks=100)
        TestResult.objects.create(test=test, student=self.student1, score=60)

        response = self.client.get(reverse('reports:student_report', args=[self.student1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '60')

    def test_csv_and_pdf_download(self):
        self.login_teacher()
        response = self.client.get(reverse('reports:student_report_csv', args=[self.student1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        response = self.client.get(reverse('reports:student_report_pdf', args=[self.student1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_homework_due_false_excluded_from_rate(self):
        self.login_teacher()
        session1 = ClassSession.objects.create(teacher_class=self.teacher_class, date=timezone.localdate())
        session2 = ClassSession.objects.create(
            teacher_class=self.teacher_class, date=timezone.localdate() - timedelta(days=1), homework_due=False
        )
        StudentSessionRecord.objects.create(session=session1, student=self.student1, homework='done')
        StudentSessionRecord.objects.create(session=session2, student=self.student1, homework='not_done')

        response = self.client.get(reverse('reports:student_report', args=[self.student1.id]))
        self.assertEqual(response.context['homework']['recorded'], 1)
        self.assertEqual(response.context['homework']['pct'], 100)


class DashboardTests(BaseReportTestCase):
    def test_dashboard_lists_classes(self):
        self.login_teacher()
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '6th Year HL')


class StudentClassNoteTests(BaseReportTestCase):
    """Standing ability/note per student, per class."""

    def note_url(self, student=None):
        return reverse(
            'reports:set_student_note',
            args=[self.teacher_class.id, (student or self.student1).id],
        )

    def post_note(self, field, value, student=None):
        return self.client.post(
            self.note_url(student),
            data=json.dumps({'field': field, 'value': value}),
            content_type='application/json',
        )

    def test_other_teacher_blocked(self):
        self.client.login(username='teacher_b', password='pw')
        response = self.post_note('ability', 'high')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(StudentClassNote.objects.exists())

    def test_ability_creates_then_updates_one_row(self):
        self.login_teacher()
        self.assertEqual(self.post_note('ability', 'high').status_code, 200)
        self.assertEqual(self.post_note('ability', 'low').status_code, 200)

        notes = StudentClassNote.objects.filter(teacher_class=self.teacher_class, student=self.student1)
        self.assertEqual(notes.count(), 1)
        self.assertEqual(notes.first().ability, 'low')

    def test_invalid_ability_rejected_and_row_untouched(self):
        self.login_teacher()
        self.post_note('ability', 'high')
        response = self.post_note('ability', 'excellent')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StudentClassNote.objects.get(student=self.student1).ability, 'high')

    def test_blank_ability_clears_rating(self):
        self.login_teacher()
        self.post_note('ability', 'medium')
        self.assertEqual(self.post_note('ability', '').status_code, 200)
        self.assertEqual(StudentClassNote.objects.get(student=self.student1).ability, '')

    def test_note_saved_and_truncated(self):
        self.login_teacher()
        self.assertEqual(self.post_note('note', 'Strong on algebra').status_code, 200)
        self.assertEqual(StudentClassNote.objects.get(student=self.student1).note, 'Strong on algebra')

        response = self.post_note('note', 'x' * 400)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(StudentClassNote.objects.get(student=self.student1).note), 300)

    def test_ability_and_note_are_independent(self):
        self.login_teacher()
        self.post_note('ability', 'high')
        self.post_note('note', 'Needs pushing')
        note = StudentClassNote.objects.get(student=self.student1)
        self.assertEqual(note.ability, 'high')
        self.assertEqual(note.note, 'Needs pushing')

    def test_unknown_field_rejected(self):
        self.login_teacher()
        response = self.post_note('grade', 'A')
        self.assertEqual(response.status_code, 400)

    def test_get_not_allowed(self):
        self.login_teacher()
        self.assertEqual(self.client.get(self.note_url()).status_code, 405)

    def test_student_outside_class_404s(self):
        outsider = User.objects.create_user(username='outsider', password='pw')
        self.login_teacher()
        response = self.client.post(
            reverse('reports:set_student_note', args=[self.teacher_class.id, outsider.id]),
            data=json.dumps({'field': 'ability', 'value': 'high'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    def test_daily_entry_renders_existing_ability_and_note(self):
        StudentClassNote.objects.create(
            teacher_class=self.teacher_class, student=self.student1,
            ability='high', note='Strong on algebra',
        )
        self.login_teacher()
        response = self.client.get(reverse('reports:daily_entry', args=[self.teacher_class.id]))
        self.assertContains(response, 'Strong on algebra')
        self.assertContains(response, 'data-field="ability" data-state="high"')

    def test_notes_do_not_leak_between_classes(self):
        other_class = TeacherClass.objects.create(teacher=self.teacher_profile, name='5th Year')
        other_class.students.add(self.student1)
        StudentClassNote.objects.create(
            teacher_class=self.teacher_class, student=self.student1, note='Only in 6th year',
        )
        self.login_teacher()
        response = self.client.get(reverse('reports:daily_entry', args=[other_class.id]))
        self.assertNotContains(response, 'Only in 6th year')
