"""
Django settings for lcstats project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Now you can use them like this:
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT = os.getenv("OPENAI_PROJECT")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")  # For exam marking with vision
FAQ_MATCH_THRESHOLD = float(os.getenv("FAQ_MATCH_THRESHOLD", 0.7))


# ------------------------------------------------------------
# Paths & Environment
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env in the project root
load_dotenv(BASE_DIR / ".env")

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
    'stats_simulator',
    'schools',
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
TIME_ZONE = 'UTC'
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
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# Default email addresses
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@lcaimaths.com')
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
HIJACK_ALLOW_GET_REQUESTS = True  # Allow hijacking via GET requests
HIJACK_DISPLAY_ADMIN_BUTTON = True  # Show hijack button in admin
HIJACK_USE_BOOTSTRAP = True  # Use Bootstrap styling for hijack button
