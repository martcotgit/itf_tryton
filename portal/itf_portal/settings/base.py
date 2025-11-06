from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "dev-secret-key"),
    PORTAL_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    TRYTON_RPC_URL=(str, "http://tryton:8000/"),
    TRYTON_DATABASE=(str, "tryton"),
    TRYTON_USER=(str, None),
    TRYTON_PASSWORD=(str, None),
    TRYTON_SESSION_TTL=(int, 300),
    TRYTON_TIMEOUT=(float, 10.0),
    TRYTON_RETRY_ATTEMPTS=(int, 3),
)

ENV_FILE_VAR = env("DJANGO_ENV_FILE", default=None)
if ENV_FILE_VAR:
    env.read_env(ENV_FILE_VAR)
else:
    default_env = BASE_DIR / ".env"
    if default_env.exists():
        env.read_env(str(default_env))

DEBUG = env.bool("DEBUG")
SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS = env.list("PORTAL_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "itf_portal.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "itf_portal.wsgi.application"
ASGI_APPLICATION = "itf_portal.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}

CACHES = {
    "default": env.cache("REDIS_URL", default="locmemcache://"),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

TRYTON_RPC_URL = env("TRYTON_RPC_URL")
TRYTON_DATABASE = env("TRYTON_DATABASE")
TRYTON_USER = env("TRYTON_USER")
TRYTON_PASSWORD = env("TRYTON_PASSWORD")
TRYTON_SESSION_TTL = env.int("TRYTON_SESSION_TTL")
TRYTON_TIMEOUT = env.float("TRYTON_TIMEOUT")
TRYTON_RETRY_ATTEMPTS = env.int("TRYTON_RETRY_ATTEMPTS")
