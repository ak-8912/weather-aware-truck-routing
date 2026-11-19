# Local setup

## Prerequisites

- Node.js 20.19+ or 22.12+
- Python 3.10+

## Frontend

```sh
cd frontend
cp .env.example .env
npm install
npm run dev
```

Set `VITE_API_BASE_URL` in `frontend/.env` to the Django API root (default: `http://localhost:8000/api`). Run the production TypeScript check and bundle with `npm run build`; run frontend interaction tests with `npm test`.

## Backend

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py runserver
```

Health endpoint: `http://localhost:8000/api/health/`. Add an OpenRouteService/HeiGIT API key to `backend/.env` before using routing/geocoding. Configure `OPENROUTESERVICE_BASE_URL` and `OPENROUTESERVICE_GEOCODING_BASE_URL` there only if you use a different compatible provider host. Open-Meteo access is public and needs no key for this workflow. `OPEN_METEO_TIMEOUT` and `OPEN_METEO_CACHE_SECONDS` optionally control forecast request timeouts and normalized forecast caching.

The frontend trip workflow calls `POST /api/trips/analyze/`; this composes route alternatives, ETA checkpoints, checkpoint weather, risk calculations, and route recommendation. The frontend does not contain provider credentials or fallback route/weather fixtures.

For backend tests, install `pip install -r requirements-dev.txt`; run checks with `python manage.py check` and tests with `python -m pytest` from `backend/`.

## Production configuration (provider-neutral)

Use a hosting platform that runs a Python WSGI service and a static frontend. The backend settings reject placeholder secrets, wildcard/missing hosts, non-HTTPS CORS origins, and SQLite when `DJANGO_DEBUG=False`. PostgreSQL can be configured with `DJANGO_DB_ENGINE=django.db.backends.postgresql`, `DJANGO_DB_NAME`, `DJANGO_DB_USER`, `DJANGO_DB_PASSWORD`, `DJANGO_DB_HOST`, and `DJANGO_DB_PORT`; alternatively set a PostgreSQL `DATABASE_URL`. Install backend requirements, including Gunicorn and Psycopg, and run from `backend/`:

```sh
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 60
```

Set `DJANGO_DEBUG=False`, a unique `DJANGO_SECRET_KEY`, explicit `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` with the HTTPS frontend origin, PostgreSQL settings, and `OPENROUTESERVICE_API_KEY` in the host's secret/environment manager. Add the HTTPS app and API domains to `CSRF_TRUSTED_ORIGINS` if using Django session/admin forms. Keep `DJANGO_SECURE_SSL_REDIRECT=True` when requests reach Django as HTTPS; if TLS terminates at a trusted proxy, set `DJANGO_TRUST_X_FORWARDED_PROTO=True` only when that proxy overwrites `X-Forwarded-Proto`. The host must serve `STATIC_ROOT` assets from `collectstatic` (or configure its static file service).

Build the frontend with the browser-reachable API URL present at build time:

```sh
VITE_API_BASE_URL=https://api.example.com/api npm run build
```

Publish `frontend/dist/` on a static host with SPA fallback to `index.html`. Configure the actual API and frontend origins in Django; the development CORS allowlist is not suitable for production. SQLite and Django's in-memory cache are intended for local development/single-process use; production should use PostgreSQL and a shared cache if running multiple instances. Provider keys must be stored in platform secrets, not frontend build variables. Deployment remains unverified until run on the chosen host.
