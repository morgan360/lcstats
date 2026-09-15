"""Turning an emailed scan into waiting scans, and waiting scans into checks.

The raw email arrives from the Cloudflare Email Worker exactly as it was sent.
Parsing is done here rather than in the Worker so that the Worker stays a few
lines long and everything that can go wrong with an attachment is tested in
Python.
"""
import logging
import re
from email import policy
from email.parser import BytesParser

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from students.services.image_intake import (
    ImageIntakeError, is_pdf, pdf_page_count, pdf_thumbnail, process_pdf_pages,
)

from ..models import CheckPhoto, HomeworkCheck, InboundScan, ScanAddress

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r'^scans\+([a-z0-9]{6,16})@', re.IGNORECASE)


def teacher_for_recipient(recipient):
    """The teacher whose scan address this is, or None.

    The Worker passes Cloudflare's envelope recipient, which keeps the +token
    that subaddressing adds. Anything else -- plain scans@, a mistyped token --
    matches no one.
    """
    match = _TOKEN_RE.match((recipient or '').strip())
    if not match:
        return None
    address = (ScanAddress.objects.select_related('teacher')
               .filter(token=match.group(1).lower()).first())
    return address.teacher if address else None


def _is_body_part(part):
    """The text of the email itself, which is not a scan."""
    return (part.get_content_maintype() == 'text'
            and part.get_content_disposition() != 'attachment'
            and not part.get_filename())


def store_email(teacher, raw):
    """Save each PDF in the email as a waiting scan. Returns how many rows.

    Always leaves at least one row, so the teacher can see that an email came
    even when nothing in it could be used: a copier set to send JPEG, a scan
    that was never attached. Inline images that are not PDFs (a logo in a
    signature) are only mentioned when there is no PDF at all, so a normal scan
    email does not come with noise beside it.
    """
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    sender = str(msg.get('From', '') or '')[:254]
    subject = str(msg.get('Subject', '') or '')[:200]

    pdfs, others = [], []
    for part in msg.walk():
        if part.is_multipart() or _is_body_part(part):
            continue
        payload = part.get_payload(decode=True) or b''
        if not payload:
            continue
        name = part.get_filename() or ''
        if is_pdf(payload):
            pdfs.append((name, payload))
        else:
            others.append(name or part.get_content_type())

    def new_scan(filename):
        return InboundScan(teacher=teacher, sender=sender, subject=subject,
                           filename=(filename or 'scan.pdf')[:200])

    if not pdfs:
        scan = new_scan(others[0] if others else '')
        scan.problem = (
            f"No PDF in this email (it had {', '.join(others)[:120]}). Scan to "
            f"PDF and send it again." if others else
            "No PDF was attached to this email."
        )[:200]
        scan.save()
        return 1

    limit = getattr(settings, 'HOMEWORK_CHECK_MAX_PHOTOS', 16)
    for name, payload in pdfs:
        scan = new_scan(name)
        try:
            scan.page_count = pdf_page_count(payload)
            thumb = pdf_thumbnail(payload)
        except ImageIntakeError as e:
            scan.problem = str(e)[:200]
            scan.save()
            continue
        if scan.page_count > limit:
            scan.problem = (f"{scan.page_count} pages, and a check takes at most "
                            f"{limit}. Scan single-sided, or split it.")
        scan.pdf.save('scan.pdf', ContentFile(payload), save=False)
        scan.thumbnail.save('first-page.jpg', thumb, save=False)
        scan.save()
    return len(pdfs)


def create_check_from_scan(scan, *, teacher, teacher_class, student, solution,
                           exercise_name, solution_pages):
    """Make a check whose photos are the scan's pages, then drop the scan.

    Raises ImageIntakeError if the PDF can't be turned into pages; the scan is
    left in place, with the reason on it, for the teacher to see.
    """
    with scan.pdf.open('rb') as fh:
        data = fh.read()
    limit = getattr(settings, 'HOMEWORK_CHECK_MAX_PHOTOS', 16)
    pages = process_pdf_pages(data, max_pages=limit)

    with transaction.atomic():
        check = HomeworkCheck.objects.create(
            teacher=teacher, teacher_class=teacher_class, student=student,
            solution=solution, exercise_name=exercise_name[:200],
            solution_pages=solution_pages[:60],
        )
        for order, (content, width, height, size) in enumerate(pages):
            row = CheckPhoto(hw_check=check, order=order, image_width=width,
                             image_height=height, byte_size=size)
            row.image.save(f"{order}.jpg", content, save=False)
            row.save()

    # After the check is safely made, never before: a failure above leaves the
    # scan to try again rather than losing it.
    scan.delete()
    return check
