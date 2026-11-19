from unittest import TestCase
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured

from config.settings import database_config


class DatabaseSettingsTests(TestCase):
    @patch("config.settings.DEBUG", False)
    @patch.dict("os.environ", {"DJANGO_DB_ENGINE": "django.db.backends.postgresql", "DJANGO_DB_NAME": "routing", "DJANGO_DB_USER": "driver", "DJANGO_DB_PASSWORD": "secret@with/slash", "DJANGO_DB_HOST": "postgres", "DJANGO_DB_PORT": "5432", "DATABASE_SSLMODE": "require"}, clear=True)
    def test_postgres_environment_fields_do_not_require_url_escaping(self):
        self.assertEqual(database_config(), {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "routing",
            "USER": "driver",
            "PASSWORD": "secret@with/slash",
            "HOST": "postgres",
            "PORT": "5432",
            "CONN_MAX_AGE": 60,
            "OPTIONS": {"sslmode": "require"},
        })

    @patch("config.settings.DEBUG", False)
    @patch.dict("os.environ", {"DJANGO_DB_ENGINE": "django.db.backends.postgresql", "DJANGO_DB_NAME": "", "DJANGO_DB_USER": "driver", "DJANGO_DB_PASSWORD": "secret", "DJANGO_DB_HOST": "postgres"}, clear=True)
    def test_postgres_requires_database_and_host(self):
        with self.assertRaises(ImproperlyConfigured):
            database_config()

    @patch("config.settings.DEBUG", False)
    @patch.dict("os.environ", {"DATABASE_URL": "sqlite:////tmp/routing.sqlite3"}, clear=True)
    def test_production_rejects_sqlite(self):
        with self.assertRaises(ImproperlyConfigured):
            database_config()

    @patch("config.settings.DEBUG", False)
    @patch.dict("os.environ", {}, clear=True)
    def test_production_requires_explicit_database(self):
        with self.assertRaises(ImproperlyConfigured):
            database_config()

    @patch("config.settings.DEBUG", False)
    @patch.dict("os.environ", {"DATABASE_URL": "postgresql://driver:secret@ep-example-pooler.us-east-2.aws.neon.tech/routing", "DATABASE_SSLMODE": "require"}, clear=True)
    def test_neon_pooled_url_uses_transaction_pooler_safe_settings(self):
        self.assertEqual(database_config(), {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "routing",
            "USER": "driver",
            "PASSWORD": "secret",
            "HOST": "ep-example-pooler.us-east-2.aws.neon.tech",
            "PORT": "5432",
            "CONN_MAX_AGE": 0,
            "DISABLE_SERVER_SIDE_CURSORS": True,
            "OPTIONS": {"sslmode": "require"},
        })
