from .base import *  # noqa

DEBUG = env.bool("DEBUG", default=True)
SECRET_KEY = env("SECRET_KEY", default="local-secret-key")
PORTAL_ALLOW_ALL_HOSTS = env.bool("PORTAL_ALLOW_ALL_HOSTS", default=True)
if PORTAL_ALLOW_ALL_HOSTS:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = env.list(
        "PORTAL_ALLOWED_HOSTS",
        default=["localhost", "127.0.0.1", "portal", "portal.localhost"],
    )

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

INTERNAL_IPS = ["127.0.0.1"]

# Use SQLite locally unless a DATABASE_URL is provided.
if "DATABASE_URL" not in env.ENVIRON:
    DATABASES["default"] = {  # type: ignore[name-defined]
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # type: ignore[name-defined]
    }
