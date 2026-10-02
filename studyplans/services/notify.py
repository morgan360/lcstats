"""Email a student when a study plan goes live for them.

A plan is live once it is active: created active for one student or a class, or
a draft the teacher makes active. Drafts are invisible to the student, so they
are never emailed. Each plan is emailed once at most, recorded as a 'notified'
event, so making a plan active again after an archive does not repeat it.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

from studyplans.models import StudyPlanEvent

logger = logging.getLogger(__name__)


def notify_students(plans):
    """Email each active, not-yet-notified plan's student, over one connection.

    Returns {'sent', 'failed', 'no_email'}. Never raises: a mail failure must not
    undo the plan the teacher just set.
    """
    result = {'sent': 0, 'failed': 0, 'no_email': 0}
    due = []
    for plan in plans:
        if plan.status != 'active' or plan.events.filter(kind='notified').exists():
            continue
        if not plan.student.email:
            result['no_email'] += 1
            continue
        due.append(plan)
    if not due:
        return result

    try:
        connection = get_connection()
        connection.open()
    except Exception as e:
        logger.error(f"Could not open the mail connection for study plan emails: {e}")
        result['failed'] = len(due)
        return result

    try:
        for plan in due:
            context = {
                'student': plan.student,
                'plan': plan,
                'topics': [g.topic.name for g in plan.goals.select_related('topic')],
                'teacher_name': str(plan.teacher),
                'site_url': settings.SITE_URL,
            }
            try:
                email = EmailMultiAlternatives(
                    subject=f"Your new study plan: {plan.title}",
                    body=render_to_string('studyplans/emails/plan_active.txt', context),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[plan.student.email],
                    bcc=settings.NOTIFICATION_BCC,
                    connection=connection,
                )
                email.attach_alternative(
                    render_to_string('studyplans/emails/plan_active.html', context), "text/html")
                email.send()
            except Exception as e:
                logger.error(f"Failed to send study plan email to {plan.student.email}: {e}")
                result['failed'] += 1
                continue
            StudyPlanEvent.log(plan, 'notified', f"Emailed {plan.student.email} that the plan is live")
            result['sent'] += 1
    finally:
        connection.close()
    return result


def describe(result):
    """A short line for the teacher's message bar, or '' when nothing happened."""
    bits = []
    if result['sent']:
        bits.append(f"Emailed {result['sent']} student(s).")
    if result['failed']:
        bits.append(f"{result['failed']} email(s) failed to send.")
    if result['no_email']:
        bits.append(f"{result['no_email']} student(s) have no email address.")
    return " ".join(bits)
