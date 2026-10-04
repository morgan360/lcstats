---
description: Deploy NumScoil to production (PythonAnywhere, numscoil.ie) and understand its settings there - the Cloudflare proxy setup, static file serving, and the collectstatic step a static/ change needs before it is really live. Read before deploying, before changing anything under static/, and when a deployed asset 404s or a script's functions are undefined.
name: deploying
---

# Deploying to production

**Security (settings.py, lines 56-85):**
- Cloudflare proxy setup: Uses `X-Forwarded-Proto` header for HTTPS detection
- `SECURE_SSL_REDIRECT` disabled to prevent redirect loops with Cloudflare
- HSTS enabled with 1-year expiry, subdomains, and preload
- Session/CSRF cookies marked secure in production
- `X_FRAME_OPTIONS = 'SAMEORIGIN'` to allow video controls

**Static Files:**
- `STATICFILES_DIRS = [BASE_DIR / "static"]` - Development static files
- `STATIC_ROOT = BASE_DIR / "staticfiles"` - Production collected statics
- `MEDIA_ROOT = BASE_DIR / "media"` - User uploads (marking schemes, images)

**Any change under `static/` needs `collectstatic` on production, plus a reload.**
Production serves `/static/` from `staticfiles/`, not from `static/`, so a file
copied to `static/` alone is a 404 however correct the code referencing it is.
This bites hardest with a *new* file: the page still renders, the `<script>` tag
is right there in the HTML, and the only symptom is that its functions are
undefined -- a dropdown that does nothing, a button that does not respond.
Nothing in the server log says so.

    ./venv/bin/python manage.py collectstatic --noinput
    touch /var/www/www_numscoil_ie_wsgi.py

Verify by fetching the file, not by eye:

    curl -s -o /dev/null -w "%{http_code}\n" https://www.numscoil.ie/static/js/<file>

**Cloudflare caches the 404.** numscoil.ie sits behind Cloudflare, so an asset
that 404'd before `collectstatic` keeps 404ing afterwards until the cache
expires. Add a query string (`?v=123`) to check whether it is really fixed --
if the busted URL returns 200 and the plain one does not, the file is fine and
you are looking at cache. Hard-refresh the browser too.

**Environment Detection:**
- `DEBUG = os.getenv('DEBUG', 'False') == 'True'` - Explicit opt-in for debug mode
- `SECRET_KEY` MUST be set in `.env` - raises `ValueError` if missing
- `ALLOWED_HOSTS` parsed from comma-separated env variable
