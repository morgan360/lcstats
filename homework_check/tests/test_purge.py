"""The retention promise: photos go after a few days, the report stays.

Photographs of a named child's work have to actually leave the disk, and the
marked report -- the student's history -- must survive their going. Both
halves are asserted, because either one failing alone looks fine from outside.
"""
import os
import shutil
import tempfile
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from homework.models import TeacherClass
from homework_check.models import CheckPhoto, HomeworkCheck
from hw_solutions.models import HWSolution

from .test_views import make_teacher, photo

PRIVATE_ROOT = tempfile.mkdtemp(prefix="hwcheck-purge-test-")


@override_settings(PRIVATE_MEDIA_ROOT=PRIVATE_ROOT,
                   HOMEWORK_CHECK_PHOTO_RETENTION_DAYS=7)
class PhotoPurgeTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(PRIVATE_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.teacher, profile = make_teacher('teacher_a')
        from django.contrib.auth.models import User
        self.student = User.objects.create_user('aoife', password='pw')
        self.teacher_class = TeacherClass.objects.create(
            teacher=profile, name='6th Year HL')
        self.teacher_class.students.add(self.student)
        self.solution = HWSolution.objects.create(title='Ex 2.1', page_count=2)
        self.client.login(username='teacher_a', password='pw')
        self.check = self.make_check()

    def make_check(self, **fields):
        defaults = dict(
            teacher=self.teacher, teacher_class=self.teacher_class,
            student=self.student, solution=self.solution,
            exercise_name='Ex 2.1', status=HomeworkCheck.Status.COMPLETE,
            summary='Good work on the elimination.',
            findings=[{'label': '5', 'verdict': 'correct', 'comment': 'Fine.'}],
            rating='good',
        )
        defaults.update(fields)
        return HomeworkCheck.objects.create(**defaults)

    def add_photos(self, check, n=2, days_old=0):
        for _ in range(n):
            self.client.post(
                reverse('homework_check:check_upload', args=[check.pk]),
                {'photo': photo()})
        CheckPhoto.objects.filter(hw_check=check).update(
            created_at=timezone.now() - timedelta(days=days_old))
        return [p.image.path for p in check.photos.all()]

    def purge(self, *args):
        out = StringIO()
        call_command('purge_homework_checks', *args, stdout=out)
        return out.getvalue()

    # -- the promise ------------------------------------------------------

    def test_old_photos_leave_the_disk(self):
        paths = self.add_photos(self.check, days_old=8)
        self.assertTrue(all(os.path.exists(p) for p in paths))

        self.purge()

        self.assertFalse(any(os.path.exists(p) for p in paths))
        self.assertFalse(CheckPhoto.objects.filter(hw_check=self.check).exists())

    def test_the_report_survives_its_photos(self):
        self.add_photos(self.check, days_old=8)
        self.purge()

        self.check.refresh_from_db()
        self.assertEqual(self.check.summary, 'Good work on the elimination.')
        self.assertEqual(self.check.findings[0]['label'], '5')
        self.assertEqual(self.check.rating, 'good')
        self.assertEqual(self.check.status, HomeworkCheck.Status.COMPLETE)
        self.assertEqual(self.check.photos_deleted_count, 2)
        self.assertIsNotNone(self.check.photos_deleted_at)

    def test_recent_photos_are_kept(self):
        paths = self.add_photos(self.check, days_old=6)
        self.purge()
        self.assertTrue(all(os.path.exists(p) for p in paths))
        self.check.refresh_from_db()
        self.assertFalse(self.check.photos_deleted)

    def test_the_clock_runs_from_the_newest_photo(self):
        """An old check given a fresh photo keeps all of them until that one ages."""
        self.add_photos(self.check, n=1, days_old=20)
        self.client.post(
            reverse('homework_check:check_upload', args=[self.check.pk]),
            {'photo': photo()})
        self.purge()
        self.assertEqual(self.check.photos.count(), 2)

    def test_dry_run_deletes_nothing(self):
        paths = self.add_photos(self.check, days_old=8)
        output = self.purge('--dry-run')
        self.assertIn('Would delete 2 photo(s) from 1 check(s)', output)
        self.assertTrue(all(os.path.exists(p) for p in paths))

    def test_a_second_run_changes_nothing(self):
        self.add_photos(self.check, days_old=8)
        self.purge()
        first = HomeworkCheck.objects.get(pk=self.check.pk).photos_deleted_at
        self.purge()
        again = HomeworkCheck.objects.get(pk=self.check.pk)
        self.assertEqual(again.photos_deleted_at, first)
        self.assertEqual(again.photos_deleted_count, 2)

    def test_an_unmarked_draft_goes_with_its_photos(self):
        """No report and no photos left means nothing worth keeping."""
        draft = self.make_check(status=HomeworkCheck.Status.DRAFT, summary='',
                                findings=[], rating='')
        HomeworkCheck.objects.filter(pk=draft.pk).update(
            created_at=timezone.now() - timedelta(days=9))
        self.add_photos(draft, days_old=8)
        self.purge()
        self.assertFalse(HomeworkCheck.objects.filter(pk=draft.pk).exists())

    # -- a check with no photos left --------------------------------------

    def test_the_page_says_what_happened_and_keeps_the_report(self):
        self.add_photos(self.check, days_old=8)
        self.purge()
        response = self.client.get(
            reverse('homework_check:check_detail', args=[self.check.pk]))
        # The sentence wraps across template lines; compare it as read.
        text = ' '.join(response.content.decode().split())
        self.assertIn('The 2 photos of this copy were deleted on', text)
        self.assertContains(response, 'Good work on the elimination.')
        # The script binds to these by id, so they must still be in the page.
        for element_id in ('addPhotos', 'fileInput', 'photoGrid', 'runCheck'):
            self.assertContains(response, f'id="{element_id}"')

    def test_no_new_photos_on_a_purged_check(self):
        self.add_photos(self.check, days_old=8)
        self.purge()
        body = self.client.post(
            reverse('homework_check:check_upload', args=[self.check.pk]),
            {'photo': photo()}).json()
        self.assertFalse(body['success'])
        self.assertIn('deleted', body['message'])
        self.assertFalse(self.check.photos.exists())

    def test_a_purged_check_cannot_be_marked_again(self):
        self.add_photos(self.check, days_old=8)
        self.purge()
        body = self.client.post(
            reverse('homework_check:analyse_next', args=[self.check.pk])).json()
        self.assertFalse(body['success'])
        self.assertIn('deleted', body['message'])

    def test_the_printed_sheet_still_prints(self):
        self.add_photos(self.check, days_old=8)
        self.purge()
        response = self.client.get(
            reverse('homework_check:report_print', args=[self.check.pk]))
        self.assertContains(response, 'Good work on the elimination.')
