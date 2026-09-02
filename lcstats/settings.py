"""
Django settings for lcstats project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Must happen before any os.getenv() below, or .env values are silently ignored
load_dotenv(BASE_DIR / ".env")

# Now you can use them like this:
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT = os.getenv("OPENAI_PROJECT")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
# Answer grading can differ from the tutor bot: it is higher volume and its
# output is a mark on a student's record, not a chat reply.
OPENAI_GRADING_MODEL = os.getenv("OPENAI_GRADING_MODEL", OPENAI_CHAT_MODEL)
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")  # For exam marking with vision
# Vision calls run synchronously inside the request, so an untimed one holds a
# web worker open for as long as the API takes to give up.
OPENAI_VISION_TIMEOUT = float(os.getenv("OPENAI_VISION_TIMEOUT", 90))
# Long edge, in pixels, of the copy of a photo sent to the vision API. The API
# tiles images at 512px, so past ~1024 you pay linearly more tokens for detail
# the model does not use.
WORK_PHOTO_API_MAX_EDGE = int(os.getenv("WORK_PHOTO_API_MAX_EDGE", 1024))
# Long edge of the copy kept on disk -- what the student sees back.
WORK_PHOTO_STORE_MAX_EDGE = int(os.getenv("WORK_PHOTO_STORE_MAX_EDGE", 1600))
WORK_PHOTO_MAX_BYTES = int(os.getenv("WORK_PHOTO_MAX_BYTES", 8 * 1024 * 1024))
WORK_PHOTO_RETENTION_DAYS = int(os.getenv("WORK_PHOTO_RETENTION_DAYS", 90))
WORK_PHOTO_HOURLY_LIMIT = int(os.getenv("WORK_PHOTO_HOURLY_LIMIT", 20))
# How long the QR stays good for. Long enough to find your copy and take a
# photo, short enough that a code left on screen goes stale.
WORK_UPLOAD_TOKEN_MAX_AGE = int(os.getenv("WORK_UPLOAD_TOKEN_MAX_AGE", 900))
# While the feature is being trialled, only staff see the camera button and
# only staff can open an upload slot. Set WORK_PHOTO_STAFF_ONLY=False in the
# environment to open it to students -- no code change, no redeploy.
WORK_PHOTO_STAFF_ONLY = os.getenv("WORK_PHOTO_STAFF_ONLY", "True") == "True"

# --- Homework Check (teacher marks a student's exercise from photos) --------
# Sixteen photos is one full exercise off an iPhone. They are analysed in
# chunks because sixteen photos plus the solution pages in a single request
# would run past OPENAI_VISION_TIMEOUT and hold a web worker open -- these
# calls are synchronous and there is no background queue.
HOMEWORK_CHECK_MAX_PHOTOS = int(os.getenv("HOMEWORK_CHECK_MAX_PHOTOS", 16))
HOMEWORK_CHECK_CHUNK_SIZE = int(os.getenv("HOMEWORK_CHECK_CHUNK_SIZE", 4))
HOMEWORK_CHECK_HOURLY_LIMIT = int(os.getenv("HOMEWORK_CHECK_HOURLY_LIMIT", 40))
HOMEWORK_CHECK_RETENTION_DAYS = int(os.getenv("HOMEWORK_CHECK_RETENTION_DAYS", 90))
# The solution pages go to the model with every batch of photos, but they are
# sent first and identically every time, so from the second batch on they are
# served from the prompt cache -- and the same holds for the second and
# twenty-fifth student marked against the same pages. Measured on the real
# Algebra chapter: 10,368 of 14,328 input tokens cached on every batch after
# the first. That is what makes 30 affordable where 12 was not, and 30 covers
# every section in the book, Revision Exercises (29pp) included.
#
# It is still a cap rather than no cap: the pages also have to be rendered,
# encoded and read within OPENAI_VISION_TIMEOUT, and none of that is cached.
HOMEWORK_CHECK_MAX_SOLUTION_PAGES = int(os.getenv("HOMEWORK_CHECK_MAX_SOLUTION_PAGES", 30))
FAQ_MATCH_THRESHOLD = float(os.getenv("FAQ_MATCH_THRESHOLD", 0.7))

# NumSkull "site help" matching (pure retrieval, no GPT call — see chat/views.py).
# Above SITE_HELP_MATCH_THRESHOLD: show the matched note confidently.
# Between the floor and the threshold: show it with a hedging preface.
# Below SITE_HELP_MIN_CONFIDENCE: treat as no match and fall back to the
# general maths-tutor behavior instead of showing an irrelevant note.
# Calibrated empirically against real site-help note embeddings: well-phrased
# "how do I..." questions score ~0.5-0.65 against their matching note, while
# genuine maths questions and unrelated text score ~0.2-0.3 (see git history
# for the sample queries used to calibrate this).
SITE_HELP_MATCH_THRESHOLD = float(os.getenv("SITE_HELP_MATCH_THRESHOLD", 0.55))
SITE_HELP_MIN_CONFIDENCE = float(os.getenv("SITE_HELP_MIN_CONFIDENCE", 0.35))

# Floor for injecting notes as background context into a NumSkull prompt.
# Below this a note is not actually about the question (a slope query matching
# "The Mean" at 0.29, say), so passing it to the model adds noise, not grounding.
RAG_CONTEXT_MIN_SCORE = float(os.getenv("RAG_CONTEXT_MIN_SCORE", 0.45))


# ------------------------------------------------------------
# OpenAI Configuration
# ------------------------------------------------------------
# Store these values as Django settings so other apps can access them safely
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID")

# You can create the client later inside your app code, not here:
# from openai import OpenAI
# client = OpenAI(api_key=OPENAI_API_KEY, organization=OPENAI_ORG_ID)
# (Don’t create the client at import time — it runs before Django setup.)
# ------------------------------------------------------------

# ------------------------------------------------------------
# Core Django settings
# ------------------------------------------------------------
# CRITICAL: SECRET_KEY must be set in .env - no fallback for security
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in .env file")

# DEBUG: Default to False for safety - must explicitly set True in development
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Parse ALLOWED_HOSTS from environment variable, remove empty strings
allowed_hosts_str = os.getenv('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(',') if host.strip()]

# ------------------------------------------------------------
# Security Settings for HTTPS/SSL (Cloudflare-aware)
# ------------------------------------------------------------
# Only enable these in production (when DEBUG=False)
if not DEBUG:
    # DO NOT use SECURE_SSL_REDIRECT with Cloudflare proxy
    # Cloudflare handles HTTPS redirect via "Always Use HTTPS" setting in Edge Certificates
    # Using SECURE_SSL_REDIRECT can cause redirect loops because:
    # - Cloudflare -> PythonAnywhere uses HTTP internally
    # - Django sees HTTP and tries to redirect to HTTPS
    # - But the user is already on HTTPS (via Cloudflare)
    # SECURE_SSL_REDIRECT = False  # Explicitly disabled for Cloudflare

    # HSTS (HTTP Strict Transport Security)
    # Cloudflare also provides HSTS, but Django-level is defense-in-depth
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Session and CSRF cookies - require HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # CSRF trusted origins - required for Django 4.0+ with HTTPS
    CSRF_TRUSTED_ORIGINS = [
        'https://numscoil.ie',
        'https://www.numscoil.ie',
    ]

    # CRITICAL: Trust Cloudflare proxy headers for HTTPS detection
    # Cloudflare sends X-Forwarded-Proto: https when user connects via HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Additional security headers
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    # Use SAMEORIGIN instead of DENY to allow video controls to work properly
    # DENY can interfere with video player functionality in some browsers
    X_FRAME_OPTIONS = 'SAMEORIGIN'

INSTALLED_APPS = [
    # django-autocomplete-light must be before django.contrib.admin
    'dal',
    'dal_select2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Required for allauth
    # allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # Third-party apps
    'django_select2',  # Searchable dropdowns
    # My Apps
    'core',  # Core models (Subject, etc.)
    'home',
    'notes',
    'chat',
    'interactive_lessons',
    'students',
    'revision',
    'cheatsheets',
    'exam_papers',
    'quickkicks',
    'flashcards',
    'homework',
    'hw_solutions',
    'stats_simulator',
    'schools',
    'reports',
    'homework_check',
    'hijack',
    'hijack.contrib.admin',
]
INSTALLED_APPS += ['markdownx']
INSTALLED_APPS += ["markdownify"]
MARKDOWNIFY = {"default": {"BLEACH": False}}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'lcstats.middleware.WWWRedirectMiddleware',  # Redirect non-www to www
    'django.contrib.sessions.middleware.SessionMiddleware',
    'core.middleware.SubjectMiddleware',  # Track current subject (Maths/Physics)
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Required for allauth
    'hijack.middleware.HijackUserMiddleware',  # Required for django-hijack
    'students.middleware.SessionActivityMiddleware',
]

ROOT_URLCONF = 'lcstats.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'homework.context_processors.homework_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'lcstats.wsgi.application'

# ------------------------------------------------------------
# Database
# ------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "lcaim"),
        "USER": os.getenv("DB_USER", "morgan"),
        "PASSWORD": os.getenv("DB_PASSWORD", "help1234"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}


# ------------------------------------------------------------
# Password validation
# ------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ------------------------------------------------------------
# Internationalization
# ------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Dublin'
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------
# Static files
# ------------------------------------------------------------
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # for production (optional)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Student-uploaded photos of their own work. Deliberately NOT under MEDIA_ROOT:
# in production /media/ is a web-server static mapping served without ever
# reaching Django, so anything in it is public at a guessable URL and cannot be
# permission-checked. This directory has no such mapping and is only ever
# reachable through students.views.work_photo, which checks ownership.
# DO NOT add a static mapping for it on PythonAnywhere.
PRIVATE_MEDIA_ROOT = Path(os.getenv("PRIVATE_MEDIA_ROOT", BASE_DIR / "private_media"))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/interactive/'
LOGOUT_REDIRECT_URL = '/'

# ------------------------------------------------------------
# Email Configuration
# ------------------------------------------------------------
# Email backend for sending emails
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

# SMTP settings (only needed if using SMTP backend in production)
# Brevo SMTP relay: EMAIL_HOST_USER is the Brevo account login,
# EMAIL_HOST_PASSWORD is an SMTP key (not the account password)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp-relay.brevo.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# Default email addresses
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'NumScoil <admin@numscoil.ie>')
SERVER_EMAIL = os.getenv('SERVER_EMAIL', 'admin@numscoil.ie')
TEACHER_EMAIL = os.getenv('TEACHER_EMAIL', 'morganmcknight@gmail.com')

# ------------------------------------------------------------
# Django Allauth Configuration
# ------------------------------------------------------------
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of allauth
    'django.contrib.auth.backends.ModelBackend',
    # allauth specific authentication methods, such as login by email
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Allauth settings
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # 'optional' or 'mandatory' - users can verify later
ACCOUNT_LOGOUT_ON_GET = False  # Require POST to logout for security
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_FORMS = {
    'signup': 'students.forms.SignupFormWithCode',
}

# ------------------------------------------------------------
# Google sign-in (allauth socialaccount)
# ------------------------------------------------------------
# Credentials come from the environment rather than a SocialApp row in the
# database, so they live alongside every other secret and deploy with the
# environment. Note that allauth accepts only one source: if a SocialApp row
# also exists, get_app() raises MultipleObjectsReturned and the login page
# 500s. students/checks.py guards against that combination.
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '')

# The APPS entry is only added when a key is actually present. An app with a
# blank client_id would still be advertised by {% get_providers %}, giving a
# "Continue with Google" button that fails on click; leaving it out means the
# login page quietly falls back to password-only.
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS['google']['APPS'] = [{
        'client_id': GOOGLE_CLIENT_ID,
        'secret': GOOGLE_CLIENT_SECRET,
        'key': '',
    }]

# Signing up with Google still requires a registration code: auto-signup is off
# so allauth always renders the intermediate form below, which asks for one.
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_FORMS = {
    'signup': 'students.forms.SocialSignupFormWithCode',
}

# Let existing students sign in with Google on the email they registered with,
# instead of dead-ending on "email already taken" at the signup form.
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

# Email confirmation and verification
ACCOUNT_EMAIL_REQUIRED = True  # Email is required during signup
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3  # Confirmation link expires in 3 days
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[NumScoil] '  # Prefix for all emails

# Password reset settings
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = '/students/dashboard/'

# Redirect URLs for allauth
ACCOUNT_LOGOUT_REDIRECT_URL = '/'

# Session behavior - remember me functionality
ACCOUNT_SESSION_REMEMBER = True  # Allow users to choose session persistence

# ------------------------------------------------------------
# Django Hijack Configuration
# ------------------------------------------------------------
HIJACK_PERMISSION_CHECK = 'hijack.permissions.superusers_only'  # Only superusers can hijack
HIJACK_LOGOUT_REDIRECT_URL = '/admin/auth/user/'  # Redirect to user list after releasing hijack
HIJACK_DISPLAY_ADMIN_BUTTON = True  # Show hijack button in admin
HIJACK_USE_BOOTSTRAP = True  # Use Bootstrap styling for hijack button

# Security: Use POST requests for hijack/release actions in production to avoid CSRF issues
# GET requests are convenient in dev but can cause CSRF errors when releasing hijack on live site
if DEBUG:
    HIJACK_ALLOW_GET_REQUESTS = True  # Allow GET in development for convenience
else:
    HIJACK_ALLOW_GET_REQUESTS = False  # Require POST in production for security
