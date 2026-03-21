import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_assignment_published_email(assignment):
    """
    Send email notifications to all assigned students when a homework assignment is published.

    Returns dict with 'sent', 'failed', and 'errors' keys.
    """
    students = assignment.get_all_assigned_students()
    students_with_email = [s for s in students if s.email]

    result = {'sent': 0, 'failed': 0, 'errors': []}

    if not students_with_email:
        return result

    for student in students_with_email:
        context = {
            'student': student,
            'assignment': assignment,
            'teacher_name': str(assignment.teacher),
            'site_url': getattr(settings, 'SITE_URL', 'https://numscoil.com'),
        }

        try:
            body_text = render_to_string('homework/emails/assignment_published.txt', context)
            body_html = render_to_string('homework/emails/assignment_published.html', context)

            email = EmailMultiAlternatives(
                subject=f"New Homework: {assignment.title}",
                body=body_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[student.email],
            )
            email.attach_alternative(body_html, "text/html")
            email.send()
            result['sent'] += 1
        except Exception as e:
            logger.error(f"Failed to send homework email to {student.email}: {e}")
            result['failed'] += 1
            result['errors'].append(f"{student.email}: {e}")

    return result
