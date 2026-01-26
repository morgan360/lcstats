from core.models import Subject


class SubjectMiddleware:
    """
    Middleware to track the current subject context in the session.
    Allows users to switch between Maths, Physics, etc.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if subject is in URL parameters (for subject switching)
        subject_slug = request.GET.get('subject')

        if subject_slug:
            # User is explicitly selecting a subject
            try:
                subject = Subject.objects.get(slug=subject_slug, is_active=True)
                request.session['current_subject'] = subject.slug
            except Subject.DoesNotExist:
                # Invalid subject, default to Maths
                request.session['current_subject'] = 'maths'
        elif 'current_subject' not in request.session:
            # No subject in session, default to Maths
            request.session['current_subject'] = 'maths'

        # Add subject to request context for easy access
        try:
            request.current_subject = Subject.objects.get(
                slug=request.session.get('current_subject', 'maths')
            )
        except Subject.DoesNotExist:
            # Fallback if something goes wrong
            request.current_subject = Subject.objects.filter(slug='maths').first()

        response = self.get_response(request)
        return response
