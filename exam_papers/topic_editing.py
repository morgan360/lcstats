"""Who can retag exam questions and their parts.

Its own module rather than a helper in views, so templates, the two print
pages and the save endpoints can all ask the same question without importing
a views module -- this imports nothing at all.

Superusers only, deliberately. Teacher accounts are is_staff (registering with
a TCH- code sets it), and a topic is shared across every class and every
student's progress page; one teacher's idea of where a question belongs should
not move it for everybody.
"""


def topic_editing_visible(user):
    """True if this user may change the topic on a question or a part.

    The save endpoints check this too -- hiding a dropdown is not access
    control, and these endpoints rewrite shared classification.
    """
    return bool(user and user.is_authenticated and user.is_superuser)
