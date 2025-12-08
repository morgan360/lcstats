from django.db.models.signals import post_save, pre_delete
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.contrib.sessions.models import Session
from django.dispatch import receiver
from django.utils import timezone
from .models import StudentProfile, LoginHistory, UserSession


@receiver(post_save, sender=User)
def create_or_update_student_profile(sender, instance, created, **kwargs):
    if created:
        StudentProfile.objects.create(user=instance)
    else:
        instance.studentprofile.save()


# -------------------------------------------------------------------------
# LOGIN/LOGOUT TRACKING
# -------------------------------------------------------------------------

def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Extract user agent from request"""
    return request.META.get('HTTP_USER_AGENT', '')


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Track successful login attempts"""
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    session_key = request.session.session_key or ''

    # Create login history record
    LoginHistory.objects.create(
        user=user,
        username_attempted=user.username,
        success=True,
        ip_address=ip_address,
        user_agent=user_agent,
        session_key=session_key
    )

    # Create or update user session record
    if session_key:
        UserSession.objects.update_or_create(
            session_key=session_key,
            defaults={
                'user': user,
                'ip_address': ip_address,
                'user_agent': user_agent,
            }
        )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Clean up session when user logs out"""
    if hasattr(request, 'session') and request.session.session_key:
        UserSession.objects.filter(session_key=request.session.session_key).delete()


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """Track failed login attempts"""
    username = credentials.get('username', '')
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    LoginHistory.objects.create(
        user=None,
        username_attempted=username,
        success=False,
        ip_address=ip_address,
        user_agent=user_agent,
        session_key=''
    )


@receiver(pre_delete, sender=Session)
def cleanup_user_session(sender, instance, **kwargs):
    """Clean up UserSession when Session is deleted"""
    UserSession.objects.filter(session_key=instance.session_key).delete()
