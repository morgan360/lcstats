"""
Custom middleware for lcstats project
"""
from django.http import HttpResponsePermanentRedirect
from django.conf import settings


class WWWRedirectMiddleware:
    """
    Redirect numscoil.ie to www.numscoil.ie
    Only active when DEBUG=False (production)
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only redirect in production
        if not settings.DEBUG:
            host = request.get_host().lower()
            # Redirect non-www to www for numscoil.ie
            if host == 'numscoil.ie':
                new_url = f"https://www.{host}{request.get_full_path()}"
                return HttpResponsePermanentRedirect(new_url)

        return self.get_response(request)