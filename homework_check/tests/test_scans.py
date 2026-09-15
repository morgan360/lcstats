"""Scans by email: the inbound endpoint, the scans page, and turning scans into checks.

The endpoint is public by necessity -- a Cloudflare Worker posts to it -- so the
first thing asserted is that without the secret it is simply not there. Then
that scans are private to their teacher the way photos are, and that a scan
turned into a check leaves nothing of itself behind on disk.
"""
import io
import os
import shutil
import tempfile
from datetime import timedelta
from email.message import EmailMessage
from io import StringIO

import fitz
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from homework.models import TeacherClass
from homework_check.models import CheckPhoto, HomeworkCheck, InboundScan, ScanAddress
from hw_solutions.models import HWSolution

from .test_views import make_teacher

PRIVATE_ROOT = tempfile.mkdtemp(prefix="hwcheck-scans-test-")
SECRET = "test-secret-123"


def make_pdf(pages=2, **encrypt):
    doc = fitz.open()
    for n in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Name: Aoife   Page {n + 1}", fontsize=18)
    data = doc.tobytes(**encrypt)
    doc.close()
    return data


def make_big_pdf():
    """Over Django's 2.5MB DATA_UPLOAD_MAX_MEMORY_SIZE, as real scans are."""
    noise = Image.frombytes("RGB", (1100, 1100), os.urandom(1100 * 1100 * 3))
    buffer = io.BytesIO()
    noise.save(buffer, format="PNG")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_image(page.rect, stream=buffer.getvalue())
    data = doc.tobytes()
    doc.close()
    return data


def make_email(*attachments, body="Scanned on the office copier."):
    msg = EmailMessage()
    msg["From"] = "copier@school.ie"
    msg["To"] = "scans@numscoil.ie"
    msg["Subject"] = "Scan"
    msg.set_content(body)
    for name, data, maintype, subtype in attachments:
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)
    return msg.as_bytes()


def pdf_attachment(name="scan.pdf", pages=2):
    return (name, make_pdf(pages), "application", "pdf")


@override_settings(PRIVATE_MEDIA_ROOT=PRIVATE_ROOT,
                   HOMEWORK_CHECK_INBOUND_SECRET=SECRET,
                   HOMEWORK_CHECK_PHOTO_RETENTION_DAYS=7)
class ScansTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(PRIVATE_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.teacher, profile = make_teacher('teacher_a')
        self.other_teacher, other_profile = make_teacher('teacher_b')
        self.student = User.objects.create_user('aoife', password='pw', first_name='Aoife')
        self.student2 = User.objects.create_user('ciara', password='pw', first_name='Ciara')
        self.teacher_class = TeacherClass.objects.create(teacher=profile, name='6th Year HL')
        self.teacher_class.students.add(self.student, self.student2)
        self.other_class = TeacherClass.objects.create(teacher=other_profile, name='5th Year')
        self.solution = HWSolution.objects.create(title='Algebra 2', page_count=2)
        self.address = ScanAddress.for_teacher(self.teacher)
        self.client.login(username='teacher_a', password='pw')

    def send(self, raw, to=None, secret=SECRET):
        headers = {'X-Scan-To': to or self.address.address}
        if secret is not None:
            headers['X-Scan-Secret'] = secret
        return self.client.generic(
            'POST', reverse('homework_check:inbound_email'), raw,
            content_type='message/rfc822', headers=headers)

    # -- the endpoint is locked -------------------------------------------

    @override_settings(HOMEWORK_CHECK_INBOUND_SECRET='')
    def test_no_secret_configured_means_no_endpoint(self):
        self.assertEqual(self.send(make_email(pdf_attachment())).status_code, 404)
        self.assertFalse(InboundScan.objects.exists())

    def test_wrong_or_missing_secret_is_a_404(self):
        raw = make_email(pdf_attachment())
        self.assertEqual(self.send(raw, secret='nope').status_code, 404)
        self.assertEqual(self.send(raw, secret=None).status_code, 404)
        self.assertFalse(InboundScan.objects.exists())

    def test_an_unknown_address_stores_nothing_and_says_nothing(self):
        response = self.send(make_email(pdf_attachment()), to='scans+zzzzzzzzzz@numscoil.ie')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(InboundScan.objects.exists())

    @override_settings(HOMEWORK_CHECK_INBOUND_MAX_BYTES=1000)
    def test_an_oversized_email_is_refused(self):
        self.assertEqual(self.send(make_email(pdf_attachment())).status_code, 413)
        self.assertFalse(InboundScan.objects.exists())

    # -- storing ---------------------------------------------------------

    def test_each_pdf_becomes_a_private_scan_with_a_thumbnail(self):
        response = self.send(make_email(pdf_attachment('a.pdf', 2), pdf_attachment('b.pdf', 3)))
        self.assertEqual(response.json()['stored'], 2)
        scans = list(InboundScan.objects.order_by('pk'))
        self.assertEqual([s.page_count for s in scans], [2, 3])
        self.assertEqual([s.filename for s in scans], ['a.pdf', 'b.pdf'])
        for scan in scans:
            self.assertEqual(scan.teacher, self.teacher)
            self.assertEqual(scan.problem, '')
            self.assertIn(PRIVATE_ROOT, scan.pdf.path)
            self.assertTrue(os.path.exists(scan.thumbnail.path))
            with self.assertRaises(ValueError):
                scan.pdf.url

    def test_a_scan_larger_than_django_would_buffer_still_arrives(self):
        raw = make_email(("big.pdf", make_big_pdf(), "application", "pdf"))
        self.assertGreater(len(raw), 2_621_440)
        self.assertEqual(self.send(raw).json()['stored'], 1)

    def test_an_email_with_no_pdf_still_shows_up_with_the_reason(self):
        png = io.BytesIO()
        Image.new("RGB", (800, 1000), "white").save(png, format="PNG")
        self.send(make_email(("page.png", png.getvalue(), "image", "png")))
        scan = InboundScan.objects.get()
        self.assertIn('No PDF', scan.problem)
        self.assertFalse(scan.pdf)

    def test_a_password_protected_pdf_shows_up_with_the_reason(self):
        locked = make_pdf(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw='u', owner_pw='o')
        self.send(make_email(("locked.pdf", locked, "application", "pdf")))
        self.assertIn('password', InboundScan.objects.get().problem)

    @override_settings(HOMEWORK_CHECK_MAX_PHOTOS=2)
    def test_too_many_pages_is_flagged_on_arrival(self):
        self.send(make_email(pdf_attachment(pages=3)))
        self.assertIn('3 pages', InboundScan.objects.get().problem)

    # -- privacy between teachers ----------------------------------------

    def test_another_teacher_sees_none_of_it(self):
        self.send(make_email(pdf_attachment()))
        scan = InboundScan.objects.get()
        self.client.login(username='teacher_b', password='pw')
        page = self.client.get(reverse('homework_check:scans'))
        self.assertNotContains(page, reverse('homework_check:scan_thumb', args=[scan.pk]))
        self.assertNotContains(page, self.address.token)
        self.assertEqual(self.client.get(
            reverse('homework_check:scan_thumb', args=[scan.pk])).status_code, 404)
        self.assertEqual(self.client.post(
            reverse('homework_check:scan_delete', args=[scan.pk])).status_code, 404)
        self.assertTrue(InboundScan.objects.filter(pk=scan.pk).exists())

    def test_another_teacher_cannot_make_checks_from_your_scans(self):
        self.send(make_email(pdf_attachment()))
        scan = InboundScan.objects.get()
        self.client.login(username='teacher_b', password='pw')
        self.client.post(reverse('homework_check:scans_assign'), {
            'teacher_class': self.other_class.pk, 'solution': self.solution.pk,
            'exercise_name': 'Ex 2.1', 'solution_pages': '',
            f'student_{scan.pk}': self.student.pk,
        })
        self.assertFalse(HomeworkCheck.objects.exists())
        self.assertTrue(InboundScan.objects.filter(pk=scan.pk).exists())

    def test_a_teacher_gets_their_own_address_and_the_page_shows_it(self):
        page = self.client.get(reverse('homework_check:scans'))
        self.assertContains(page, self.address.address)
        self.client.login(username='teacher_b', password='pw')
        other = self.client.get(reverse('homework_check:scans'))
        self.assertNotEqual(ScanAddress.for_teacher(self.other_teacher).token, self.address.token)
        self.assertContains(other, ScanAddress.for_teacher(self.other_teacher).address)

    # -- scans into checks -----------------------------------------------

    def assign(self, **students):
        data = {'teacher_class': self.teacher_class.pk, 'solution': self.solution.pk,
                'exercise_name': 'Ex 2.1', 'solution_pages': '3-4'}
        data.update(students)
        return self.client.post(reverse('homework_check:scans_assign'), data)

    def test_assigning_makes_checks_with_the_pages_in_order_and_drops_the_scans(self):
        self.send(make_email(pdf_attachment('a.pdf', 2), pdf_attachment('b.pdf', 3)))
        first, second = InboundScan.objects.order_by('pk')
        files = [first.pdf.path, first.thumbnail.path, second.pdf.path, second.thumbnail.path]

        response = self.assign(**{f'student_{first.pk}': self.student.pk,
                                  f'student_{second.pk}': self.student2.pk})

        checks = list(HomeworkCheck.objects.order_by('pk'))
        self.assertEqual([c.student for c in checks], [self.student, self.student2])
        self.assertEqual([c.photos.count() for c in checks], [2, 3])
        self.assertEqual(list(checks[1].photos.values_list('order', flat=True)), [0, 1, 2])
        self.assertEqual(checks[0].solution_pages, '3-4')
        for photo in CheckPhoto.objects.all():
            self.assertIn(PRIVATE_ROOT, photo.image.path)
        self.assertFalse(InboundScan.objects.exists())
        self.assertFalse(any(os.path.exists(p) for p in files))
        self.assertRedirects(
            response,
            f"{reverse('homework_check:run')}?ids={checks[0].pk},{checks[1].pk}",
            fetch_redirect_response=False)

    def test_a_scan_left_on_skip_keeps_waiting(self):
        self.send(make_email(pdf_attachment('a.pdf'), pdf_attachment('b.pdf')))
        first, second = InboundScan.objects.order_by('pk')
        self.assign(**{f'student_{first.pk}': self.student.pk, f'student_{second.pk}': ''})
        self.assertEqual(HomeworkCheck.objects.count(), 1)
        self.assertEqual(list(InboundScan.objects.all()), [second])

    def test_a_student_from_another_class_is_ignored(self):
        outsider = User.objects.create_user('niamh', password='pw')
        self.send(make_email(pdf_attachment()))
        scan = InboundScan.objects.get()
        self.assign(**{f'student_{scan.pk}': outsider.pk})
        self.assertFalse(HomeworkCheck.objects.exists())

    def test_the_batch_page_lists_the_new_checks_for_their_teacher_only(self):
        self.send(make_email(pdf_attachment()))
        scan = InboundScan.objects.get()
        self.assign(**{f'student_{scan.pk}': self.student.pk})
        check = HomeworkCheck.objects.get()
        url = f"{reverse('homework_check:run')}?ids={check.pk}"
        self.assertContains(self.client.get(url),
                            reverse('homework_check:analyse_next', args=[check.pk]))
        self.client.login(username='teacher_b', password='pw')
        self.assertEqual(self.client.get(url).status_code, 404)

    # -- retention -------------------------------------------------------

    def test_unclaimed_scans_go_after_the_retention_period(self):
        self.send(make_email(pdf_attachment('old.pdf'), pdf_attachment('new.pdf')))
        old, new = InboundScan.objects.order_by('pk')
        old_files = [old.pdf.path, old.thumbnail.path]
        InboundScan.objects.filter(pk=old.pk).update(
            received_at=timezone.now() - timedelta(days=8))

        call_command('purge_homework_checks', stdout=StringIO())

        self.assertEqual(list(InboundScan.objects.all()), [new])
        self.assertFalse(any(os.path.exists(p) for p in old_files))
