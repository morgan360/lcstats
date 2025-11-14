"""
Middleware to track user session activity
"""
from django.utils import timezone
from django.contrib.sessions.models import Session
from .models import UserSession


class SessionActivityMiddleware:
    """
    Middleware to update the last_activity timestamp for active sessions
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Update session activity before processing the request
        if request.user.is_authenticated and hasattr(request, 'session') and request.session.session_key:
            try:
                session = Session.objects.get(session_key=request.session.session_key)
                user_session = UserSession.objects.filter(session=session).first()
                if user_session:
                    # The last_activity field has auto_now=True, so it will update automatically
                    user_session.save()
            except Session.DoesNotExist:
                pass

        response = self.get_response(request)
        return response
