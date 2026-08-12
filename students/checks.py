"""System checks for the Google sign-in configuration.

allauth accepts a provider app from either SOCIALACCOUNT_PROVIDERS['google']['APPS']
or a SocialApp row in the database, but not both: get_app() raises
MultipleObjectsReturned, which surfaces as a 500 on the login page rather than
anywhere near the cause. This turns that into an error at startup.
"""

from django.conf import settings
from django.core.checks import Error, register


@register()
def google_socialapp_not_duplicated(app_configs, **kwargs):
    from_settings = bool(
        settings.SOCIALACCOUNT_PROVIDERS.get('google', {}).get('APPS')
    )
    if not from_settings:
        return []

    try:
        from allauth.socialaccount.models import SocialApp
        from_db = SocialApp.objects.filter(provider='google').exists()
    except Exception:
        # No database yet (e.g. during the first migrate) - nothing to compare.
        return []

    if not from_db:
        return []

    return [
        Error(
            "Google sign-in is configured twice: GOOGLE_OAUTH_CLIENT_ID is set "
            "in the environment and a SocialApp row exists in the database.",
            hint=(
                "allauth allows only one. Keep the environment variables and "
                "delete the row (Admin > Social accounts > Social applications), "
                "or unset GOOGLE_OAUTH_CLIENT_ID/GOOGLE_OAUTH_CLIENT_SECRET and "
                "manage the credentials in the admin instead."
            ),
            id='students.E001',
        )
    ]
