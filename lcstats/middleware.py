"""
Custom middleware for lcstats project
"""
from django.http import HttpResponsePermanentRedirect
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class WWWRedirectMiddleware:
    """
    Redirect numscoil.ie to www.numscoil.ie
    Always active (removed DEBUG check for troubleshooting)
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().lower()
        # Remove port if present
        host_without_port = host.split(':')[0]

        # Log for debugging
        logger.info(f"WWWRedirect: host={host}, host_without_port={host_without_port}, DEBUG={settings.DEBUG}")

        # Redirect non-www to www for numscoil.ie
        if host_without_port == 'numscoil.ie':
            new_url = f"https://www.numscoil.ie{request.get_full_path()}"
            logger.info(f"WWWRedirect: Redirecting to {new_url}")
            return HttpResponsePermanentRedirect(new_url)

        return self.get_response(request)