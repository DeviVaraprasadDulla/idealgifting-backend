"""
Django settings for backend project.
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

# -------------------------------------------------
# BASE CONFIG
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# 🔒 Safe fallback (avoid crash if .env missing)
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-secret-key-change-in-production")

DEBUG = os.getenv("DEBUG", "True") == "True"

# 🔒 Production-ready host handling
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

GOOGLE_CLIENT_ID = "743254433347-9g0g82eosbfoo8dt19p6ufoeegqo82vi.apps.googleusercontent.com"

# -------------------------------------------------
# REST FRAMEWORK
# -------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

# -------------------------------------------------
# INSTALLED APPS
# -------------------------------------------------

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt.token_blacklist",

    # Custom Apps
    "users",
    "products",
    "cart",
    "orders",
    "banners",
    "payments",
    "import_export",
    "settings_app",
]

# -------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------------------------
# CORS
# -------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-guest-id",
]

SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True

# 🔒 Enable secure cookies in production
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True

# -------------------------------------------------
# URLS & TEMPLATES
# -------------------------------------------------

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

# -------------------------------------------------
# DATABASE
# -------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME"),
        "USER": os.getenv("DATABASE_USER"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD"),
        "HOST": os.getenv("DATABASE_HOST"),
        "PORT": os.getenv("DATABASE_PORT"),
        "OPTIONS": {
            "options": "-c search_path=public"
        },
    }
}

# -------------------------------------------------
# PASSWORD VALIDATORS
# -------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -------------------------------------------------
# INTERNATIONALIZATION
# -------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# -------------------------------------------------
# STATIC & MEDIA
# -------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -------------------------------------------------
# JAZZMIN ADMIN UI
# -------------------------------------------------

JAZZMIN_SETTINGS = {
    "site_title": "Ideal Gifting",
    "site_header": "Ideal Gifting Admin Dashboard",
    "site_brand": "Ideal Gifting",
    "welcome_sign": "Welcome to Ideal Gifting Admin",
    "search_model": ["products.Product", "orders.Order"],
    "topmenu_links": [
        {"name": "Home", "url": "admin:index"},
    ],
    "icons": {
        "products.Product": "fas fa-box",
        "products.Category": "fas fa-list",
        "banners.Banner": "fas fa-image",
        "orders.Order": "fas fa-shopping-cart",
        "auth.User": "fas fa-user",
    },
}

# -------------------------------------------------
# JWT
# -------------------------------------------------

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CSRF_FAILURE_VIEW = "django.views.csrf.csrf_failure"

# -------------------------------------------------
# EMAIL CONFIG
# -------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

# -------------------------------------------------
# 💳 PAYMENT CONFIGURATION
# -------------------------------------------------

PAYMENT_MODE = os.getenv("PAYMENT_MODE", "DUMMY")

PHONEPE_MERCHANT_ID = os.getenv("PHONEPE_MERCHANT_ID")
PHONEPE_SALT_KEY = os.getenv("PHONEPE_SALT_KEY")
PHONEPE_SALT_INDEX = int(os.getenv("PHONEPE_SALT_INDEX", 1))

# 🔥 Safe fallback for sandbox
PHONEPE_BASE_URL = os.getenv(
    "PHONEPE_BASE_URL",
    "https://api-preprod.phonepe.com/apis/pg-sandbox"
)