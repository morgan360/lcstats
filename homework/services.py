import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_assignment_published_email(assignment):
    """
    Send email notifications to all assigned students when a homework assignment is published.

    One SMTP connection serves the whole class, rather than one login per student.
    Returns dict with 'sent', 'failed', 'no_email' and 'errors' keys.
    """
    students = list(assignment.get_all_assigned_students())
    students_with_email = [s for s in students if s.email]

    result = {'sent': 0, 'failed': 0, 'no_email': len(students) - len(students_with_email),
              'errors': []}

    if not students_with_email:
        return result

    try:
        connection = get_connection()
        connection.open()
    except Exception as e:
        logger.error(f"Could not open the mail connection for homework {assignment.pk}: {e}")
        result['failed'] = len(students_with_email)
        result['errors'].append(str(e))
        return result

    try:
        for student in students_with_email:
            context = {
                'student': student,
                'assignment': assignment,
                'teacher_name': str(assignment.teacher),
                'site_url': settings.SITE_URL,
            }

            try:
                body_text = render_to_string('homework/emails/assignment_published.txt', context)
                body_html = render_to_string('homework/emails/assignment_published.html', context)

                email = EmailMultiAlternatives(
                    subject=f"New Homework: {assignment.title}",
                    body=body_text,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[student.email],
                    bcc=settings.NOTIFICATION_BCC,
                    connection=connection,
                )
                email.attach_alternative(body_html, "text/html")
                email.send()
                result['sent'] += 1
            except Exception as e:
                logger.error(f"Failed to send homework email to {student.email}: {e}")
                result['failed'] += 1
                result['errors'].append(f"{student.email}: {e}")
    finally:
        connection.close()

    return result


def notify_if_newly_published(assignment):
    """Email the students once, the first time an assignment is saved as published.

    Call it after the assignment's classes are saved: on a new assignment they
    are written after the assignment itself, so before then it has no students.
    Returns the send result, or None when there was nothing to send.

    Never for an assignment already past its due date, so opening an old one in
    the admin cannot email students about homework they can no longer do.
    """
    if not assignment.is_published or assignment.notification_sent:
        return None
    if assignment.due_date and assignment.due_date < timezone.now():
        return None

    result = send_assignment_published_email(assignment)
    # Marked even when nobody had an address, so adding one later does not
    # replay the email for this assignment -- but not when every send failed
    # (the mail relay down), so the next save tries again.
    if result['sent'] or not result['failed']:
        assignment.notification_sent = True
        assignment.save(update_fields=['notification_sent'])
    return result
