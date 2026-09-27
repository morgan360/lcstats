import json
from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from homework.models import TeacherClass, TeacherProfile
from interactive_lessons.models import Question, QuestionPart, Topic
from quickkicks.models import QuickKick, QuickKickView
from students.models import QuestionAttempt, StudentProfile, WorkSubmission

from . import services
from .models import (
    ClassSession,
    ClassTest,
    CommentPreset,
    StudentClassNote,
    StudentSessionRecord,
    TestResult,
    TimetableSlot,
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

    def setUp(self):
        # Daily entry redirects a weekend date to Friday, so a suite run on a
        # Saturday or Sunday would see redirects instead of the page. Pin
        # "today" to the last school day; on a weekday this changes nothing.
        real_localdate = timezone.localdate
        school_day = real_localdate()
        while school_day.weekday() >= 5:
            school_day -= timedelta(days=1)

        def localdate(value=None, timezone=None):
            if value is None and timezone is None:
                return school_day
            return real_localdate(value, timezone)

        patcher = patch('django.utils.timezone.localdate', side_effect=localdate)
        patcher.start()
        self.addCleanup(patcher.stop)

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
        self.assertTrue(all(r.attendance == '' and r.homework == '' for r in session.records.all()))

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

        # Tapping round the cycle clears a chip back to not recorded
        response = self.client.post(
            url, data=json.dumps({'field': 'attendance', 'value': ''}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.attendance, '')

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
        # A photo sent by QR counts; a QR opened with no photo sent does not.
        part = QuestionPart.objects.create(question=question, label='(a)', prompt='Solve')
        for status in (WorkSubmission.Status.COMPLETE, WorkSubmission.Status.AWAITING_PHOTO):
            WorkSubmission.objects.filter(pk=WorkSubmission.objects.create(
                student=profile, question_part=part, status=status).pk).update(created_at=day)

        start = timezone.now() - timedelta(days=7)
        end = timezone.now()
        with self.assertNumQueries(6):
            activity = services.get_activity_by_day([self.student1, self.student2], start, end)

        day_key = day.date()
        self.assertEqual(activity[self.student1.id][day_key]['questions'], 2)
        self.assertEqual(activity[self.student1.id][day_key]['quickkicks'], 1)
        self.assertEqual(activity[self.student1.id][day_key]['photos'], 1)
        self.assertEqual(activity[self.student1.id][day_key]['total'], 4)
        self.assertNotIn(self.student2.id, activity)

    def test_exam_answers_count_on_the_day_they_were_submitted(self):
        """Practice reuses one open attempt per paper, so the day it started
        says nothing about when the answers came."""
        from core.models import Subject
        from exam_papers.models import (ExamAttempt, ExamPaper, ExamQuestion,
                                        ExamQuestionAttempt, ExamQuestionPart)
        paper = ExamPaper.objects.create(subject=Subject.objects.get(slug='maths'),
                                         year=2022, paper_type='p1', total_marks=300)
        part = ExamQuestionPart.objects.create(
            question=ExamQuestion.objects.create(exam_paper=paper, question_number=10,
                                                 total_marks=50),
            label='(c)', max_marks=10)
        attempt = ExamAttempt.objects.create(student=self.student1, exam_paper=paper)
        opened = timezone.now() - timedelta(days=5)
        ExamAttempt.objects.filter(pk=attempt.pk).update(started_at=opened)
        for _ in range(3):
            ExamQuestionAttempt.objects.create(exam_attempt=attempt, question_part=part,
                                               marks_awarded=7, max_marks=10)

        activity = services.get_activity_by_day(
            [self.student1], timezone.now() - timedelta(days=7), timezone.now())
        days = activity[self.student1.id]
        self.assertEqual(days[timezone.now().date()]['exams'], 3)
        self.assertNotIn(opened.date(), days)

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

    def test_blank_attendance_and_homework_excluded_from_rates(self):
        self.login_teacher()
        today = timezone.localdate()
        marked = ClassSession.objects.create(teacher_class=self.teacher_class, date=today)
        unmarked = ClassSession.objects.create(teacher_class=self.teacher_class, date=today - timedelta(days=1))
        StudentSessionRecord.objects.create(session=marked, student=self.student1, attendance='present', homework='done')
        StudentSessionRecord.objects.create(session=unmarked, student=self.student1)

        response = self.client.get(reverse('reports:student_report', args=[self.student1.id]))
        self.assertEqual(response.context['attendance']['recorded'], 1)
        self.assertEqual(response.context['attendance']['pct'], 100)
        self.assertEqual(response.context['homework']['recorded'], 1)
        self.assertEqual(response.context['homework']['pct'], 100)

        response = self.client.get(reverse('reports:class_overview', args=[self.teacher_class.id]))
        row = next(r for r in response.context['rows'] if r['student'] == self.student1)
        self.assertEqual(row['attendance_pct'], 100)
        self.assertEqual(row['homework_pct'], 100)


class DashboardTests(BaseReportTestCase):
    def test_dashboard_lists_classes(self):
        self.login_teacher()
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '6th Year HL')

    def test_opened_but_unmarked_session_is_not_recorded(self):
        today = timezone.localdate()
        slot = TimetableSlot.objects.create(
            teacher_class=self.teacher_class, weekday=today.weekday(), start_time=time(9, 0)
        )
        session = ClassSession.objects.create(teacher_class=self.teacher_class, date=today, slot=slot)
        record = StudentSessionRecord.objects.create(session=session, student=self.student1)
        self.login_teacher()

        response = self.client.get(reverse('reports:dashboard'))
        self.assertFalse(response.context['todays_classes'][0]['recorded'])

        record.attendance = 'absent'
        record.save()
        response = self.client.get(reverse('reports:dashboard'))
        self.assertTrue(response.context['todays_classes'][0]['recorded'])


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


class RosterNameTests(BaseReportTestCase):
    """Short names (no middle name) and the non-Irish asterisk."""

    def setUp(self):
        super().setUp()
        self.login_teacher()

    def roster_html(self):
        return self.client.get(
            reverse('reports:daily_entry', args=[self.teacher_class.id])
        ).content.decode()

    def test_middle_name_and_extra_surname_words_dropped(self):
        self.student1.first_name, self.student1.last_name = 'Maria Eduarda', 'Alencar Soares'
        self.student1.save()
        self.assertIn('Maria Soares', self.roster_html())

    def test_long_surname_reduced_to_last_word(self):
        self.student1.first_name = 'Francesca'
        self.student1.last_name = 'De Oliveira Castelhano Tafuri'
        self.student1.save()
        self.assertIn('Francesca Tafuri', self.roster_html())

    def test_double_barrelled_surname_keeps_first_half(self):
        self.student1.first_name, self.student1.last_name = 'Alex', 'Sadolewski-Odinakaeze'
        self.student1.save()
        html = self.roster_html()
        self.assertIn('Alex Sadolewski<', html)
        self.assertNotIn('Odinakaeze', html)

    def test_single_given_name_unchanged(self):
        self.student1.first_name, self.student1.last_name = 'Daisy', 'Nolan'
        self.student1.save()
        self.assertIn('Daisy Nolan', self.roster_html())

    def test_falls_back_to_username_when_unnamed(self):
        self.student1.first_name = self.student1.last_name = ''
        self.student1.save()
        self.assertIn('student1', self.roster_html())

    def test_non_irish_note_gets_asterisk(self):
        self.student1.first_name, self.student1.last_name = 'Julia', 'Favero'
        self.student1.save()
        StudentClassNote.objects.create(
            teacher_class=self.teacher_class, student=self.student1,
            note='Brazilian · study abroad, ends Dec 2026',
        )
        self.assertIn('Julia Favero*', self.roster_html())

    def test_irish_note_gets_no_asterisk(self):
        self.student1.first_name, self.student1.last_name = 'Daisy', 'Nolan'
        self.student1.save()
        StudentClassNote.objects.create(
            teacher_class=self.teacher_class, student=self.student1, note='Irish',
        )
        self.assertIn('Daisy Nolan<', self.roster_html())
        self.assertNotIn('Daisy Nolan*', self.roster_html())

    def test_blank_note_is_unmarked_not_foreign(self):
        self.student1.first_name, self.student1.last_name = 'Kai', 'Farrell'
        self.student1.save()
        self.assertNotIn('Kai Farrell*', self.roster_html())

    def test_ability_chip_is_inside_the_panel_not_the_front_row(self):
        html = self.roster_html()
        panel_start = html.index('comment-panel')
        ability_at = html.index('data-field="ability"')
        self.assertGreater(ability_at, panel_start,
                           "ability chip should sit inside the expandable panel")


class CreditBalanceTests(TestCase):
    """The spend page's remaining figure, counted down from an entered balance."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('boss', password='pw')
        cls.teacher, _ = make_teacher('teacher_c')

    def setUp(self):
        from django.core.cache import cache
        from . import openai_costs
        cache.delete(openai_costs.CACHE_KEY)

    def _today(self):
        import datetime as dt
        return dt.datetime.now(dt.timezone.utc).date()

    def test_openai_counts_down_without_counting_today_twice(self):
        from django.test import override_settings
        from . import openai_costs
        from .models import CreditBalance

        today = self._today()
        with override_settings(OPENAI_ADMIN_KEY='sk-admin-test'), \
                patch.object(openai_costs, '_fetch_daily_costs',
                             return_value=({today: 0.40}, 'usd')):
            row = openai_costs.record_balance(Decimal('11.55'), user=self.admin)
        self.assertEqual(row.spend_already_counted, Decimal('0.400000'))

        # Later the same day, 0.25 more has gone: only that comes off.
        with override_settings(OPENAI_ADMIN_KEY='sk-admin-test'), \
                patch.object(openai_costs, '_fetch_daily_costs',
                             return_value=({today: 0.65}, 'usd')):
            summary = openai_costs.get_cost_summary(force_refresh=True)
        self.assertAlmostEqual(summary['spent_since'], 0.25)
        self.assertAlmostEqual(summary['remaining'], 11.30)
        self.assertEqual(summary['recorded_at'], CreditBalance.latest_for('openai').recorded_at)

    def test_openai_falls_back_to_settings_before_any_balance(self):
        from django.test import override_settings
        from . import openai_costs

        today = self._today()
        with override_settings(OPENAI_ADMIN_KEY='sk-admin-test', OPENAI_CREDIT_TOPUP=8.0,
                               OPENAI_CREDIT_SINCE=today), \
                patch.object(openai_costs, '_fetch_daily_costs',
                             return_value=({today: 1.5}, 'usd')):
            summary = openai_costs.get_cost_summary(force_refresh=True)
        self.assertAlmostEqual(summary['remaining'], 6.5)
        self.assertIsNone(summary['recorded_at'])

    def test_gemini_counts_only_calls_after_the_balance(self):
        import datetime as dt
        from django.test import override_settings
        from homework_check.models import VisionUsage
        from . import gemini_spend

        entered = timezone.now() - dt.timedelta(minutes=10)
        VisionUsage.objects.create(model='gemini-x', cost_usd=Decimal('0.50'),
                                   created_at=entered - dt.timedelta(minutes=1))
        VisionUsage.objects.create(model='gemini-x', cost_usd=Decimal('0.23'),
                                   created_at=entered + dt.timedelta(minutes=1))
        row = gemini_spend.record_balance(Decimal('20.00'))
        row.recorded_at = entered
        row.save()
        with override_settings(GEMINI_USD_PER_CREDIT=1.15):
            summary = gemini_spend.get_gemini_summary()
        self.assertAlmostEqual(summary['spent_since_usd'], 0.23)
        self.assertAlmostEqual(summary['remaining'], 20 - 0.23 / 1.15)

    def test_superuser_saves_a_balance_from_the_page(self):
        from .models import CreditBalance

        self.client.login(username='boss', password='pw')
        with patch('reports.openai_costs.spend_so_far_today', return_value=0.0):
            resp = self.client.post(reverse('reports:openai_costs'),
                                    {'provider': 'openai', 'amount': '$11.55'})
        self.assertRedirects(resp, reverse('reports:openai_costs'), fetch_redirect_response=False)
        row = CreditBalance.latest_for('openai')
        self.assertEqual(row.amount, Decimal('11.55'))
        self.assertEqual(row.recorded_by, self.admin)

    def test_bad_amounts_save_nothing(self):
        from .models import CreditBalance

        self.client.login(username='boss', password='pw')
        for amount in ('', 'abc', '-3', 'NaN'):
            self.client.post(reverse('reports:openai_costs'), {'provider': 'openai', 'amount': amount})
        self.client.post(reverse('reports:openai_costs'), {'provider': 'bogus', 'amount': '5'})
        self.assertFalse(CreditBalance.objects.exists())

    def test_non_superuser_cannot_save_a_balance(self):
        from .models import CreditBalance

        self.client.login(username='teacher_c', password='pw')
        resp = self.client.post(reverse('reports:openai_costs'), {'provider': 'openai', 'amount': '5'})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(CreditBalance.objects.exists())
