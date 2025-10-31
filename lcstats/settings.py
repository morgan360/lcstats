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
SECRET_KEY = 'django-insecure-(^ho@c-=9k!bieu%$g#3gz=tt5i(@6w)rw+3)410r%xk)m&o4$'
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # My Apps
    'home',
    'notes',
    'chat',
"interactive_lessons",
    'students',
]
INSTALLED_APPS += ['markdownx']
INSTALLED_APPS += ["markdownify"]
MARKDOWNIFY = {"default": {"BLEACH": False}}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
        "NAME": "lcaim",  # <-- note the name change
        "USER": "morgan",
        "PASSWORD": "help1234",
        "HOST": "127.0.0.1",
        "PORT": "3306",
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

LOGIN_REDIRECT_URL = '/students/dashboard/'
LOGOUT_REDIRECT_URL = '/students/login/'
