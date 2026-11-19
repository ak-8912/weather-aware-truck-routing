import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
for env_file in (BASE_DIR / ".env.local", BASE_DIR / ".env"):
    load_dotenv(env_file)


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def postgres_connection_settings(host: str) -> dict:
    pooled = env_bool("DATABASE_POOLED", "-pooler." in host)
    settings = {"CONN_MAX_AGE": int(os.getenv("DATABASE_CONN_MAX_AGE", "0" if pooled else "60"))}
    if pooled:
        settings["DISABLE_SERVER_SIDE_CURSORS"] = True
    return settings


DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "").strip()
if DEBUG and not SECRET_KEY:
    SECRET_KEY = "local-development-only-not-for-production"
if not DEBUG and (not SECRET_KEY or SECRET_KEY.casefold() in {
    "replace_me", "change_me", "development-only-change-me", "replace_with_a_long_random_secret",
}):
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY to a unique secret when DJANGO_DEBUG is False.")

ALLOWED_HOSTS = [host.strip() for host in os.getenv(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else ""
).split(",") if host.strip()]
if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured("Set DJANGO_ALLOWED_HOSTS to explicit production hostnames.")

default_cors_origins = "http://localhost:5173,http://127.0.0.1:5173" if DEBUG else ""
CORS_ALLOWED_ORIGINS = [origin.strip().rstrip("/") for origin in os.getenv(
    "CORS_ALLOWED_ORIGINS", default_cors_origins
).split(",") if origin.strip()]
if not DEBUG and not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured("Set CORS_ALLOWED_ORIGINS to the browser application's HTTPS origin.")
if not DEBUG and any(not origin.startswith("https://") for origin in CORS_ALLOWED_ORIGINS):
    raise ImproperlyConfigured("CORS_ALLOWED_ORIGINS must contain HTTPS origins when DJANGO_DEBUG is False.")
CSRF_TRUSTED_ORIGINS = [origin.strip().rstrip("/") for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]


def database_config() -> dict:
    database_engine = os.getenv("DJANGO_DB_ENGINE", "").strip()
    if database_engine == "django.db.backends.postgresql":
        name = os.getenv("DJANGO_DB_NAME", "").strip()
        host = os.getenv("DJANGO_DB_HOST", "").strip()
        user = os.getenv("DJANGO_DB_USER", "").strip()
        password = os.getenv("DJANGO_DB_PASSWORD", "")
        if not name or not host or not user or not password:
            raise ImproperlyConfigured("DJANGO_DB_NAME, DJANGO_DB_USER, DJANGO_DB_PASSWORD, and DJANGO_DB_HOST are required for PostgreSQL.")
        options = {}
        sslmode = os.getenv("DATABASE_SSLMODE", "require" if not DEBUG else "prefer")
        if sslmode:
            options["sslmode"] = sslmode
        return {
            "ENGINE": database_engine,
            "NAME": name,
            "USER": user,
            "PASSWORD": password,
            "HOST": host,
            "PORT": os.getenv("DJANGO_DB_PORT", "5432"),
            **postgres_connection_settings(host),
            "OPTIONS": options,
        }
    if database_engine:
        raise ImproperlyConfigured("DJANGO_DB_ENGINE currently supports only django.db.backends.postgresql.")

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        if not DEBUG:
            raise ImproperlyConfigured("Set DATABASE_URL to a persistent PostgreSQL database in production.")
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}

    parsed = urlsplit(database_url)
    if parsed.scheme in {"postgres", "postgresql"}:
        if not parsed.hostname or not parsed.path.strip("/"):
            raise ImproperlyConfigured("DATABASE_URL must include the PostgreSQL database name and host.")
        options = {}
        sslmode = os.getenv("DATABASE_SSLMODE", "require" if not DEBUG else "prefer")
        if sslmode:
            options["sslmode"] = sslmode
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname,
            "PORT": parsed.port or "5432",
            **postgres_connection_settings(parsed.hostname),
            "OPTIONS": options,
        }
    if parsed.scheme == "sqlite":
        sqlite_path = unquote(parsed.path)
        if not DEBUG:
            raise ImproperlyConfigured("SQLite is supported for local development only; use PostgreSQL in production.")
        if sqlite_path in {"", "/", "/:memory:"}:
            name = ":memory:" if sqlite_path == "/:memory:" else BASE_DIR / "db.sqlite3"
        else:
            name = sqlite_path
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": name}
    raise ImproperlyConfigured("DATABASE_URL must use postgres://, postgresql://, or sqlite://.")


INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "corsheaders", "rest_framework",
    "apps.trips", "apps.routing", "apps.weather", "apps.risk_engine",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {"default": database_config()}
AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
}

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", not DEBUG)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", not DEBUG)
X_FRAME_OPTIONS = "DENY"
if env_bool("DJANGO_TRUST_X_FORWARDED_PROTO", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

OPENROUTESERVICE_BASE_URL = os.getenv("OPENROUTESERVICE_BASE_URL", "https://api.heigit.org/openrouteservice").rstrip("/")
OPENROUTESERVICE_GEOCODING_BASE_URL = os.getenv("OPENROUTESERVICE_GEOCODING_BASE_URL", "https://api.heigit.org/pelias/v1").rstrip("/")
OPENROUTESERVICE_TIMEOUT = float(os.getenv("OPENROUTESERVICE_TIMEOUT", "15"))
OPEN_METEO_BASE_URL = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
OPEN_METEO_TIMEOUT = float(os.getenv("OPEN_METEO_TIMEOUT", "15"))
OPEN_METEO_CACHE_SECONDS = int(os.getenv("OPEN_METEO_CACHE_SECONDS", "1800"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "config.logging.JsonLogFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}

SECRET_KEY = os.environ.get("SECRET_KEY", "unsafe-local-development-key")

DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "localhost,127.0.0.1"
).split(",")