"""Who can see photograph-your-working.

Its own module rather than a helper in views_work, so the question surfaces in
interactive_lessons and exam_papers can ask without importing a views module
and without any risk of an import cycle -- this imports nothing but settings.
"""

from django.conf import settings


def work_capture_visible(user):
    """True if this user should be offered the camera button.

    Staff-only while the feature is trialled: WORK_PHOTO_STAFF_ONLY defaults to
    True and is flipped in the environment, so opening it to students is a
    setting change rather than a deploy. The upload endpoint checks this too --
    hiding a button is not access control, and that endpoint spends money.
    """
    if not getattr(settings, "WORK_PHOTO_STAFF_ONLY", True):
        return True
    return bool(user and user.is_authenticated and user.is_staff)
