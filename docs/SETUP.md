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

Health endpoint: `http://localhost:8000/api/health/`. Add an OpenRouteService/HeiGIT API key to `backend/.env.local` before using routing/geocoding. Open-Meteo access is public and needs no key for this workflow. Provider URLs, request timeouts, and forecast caching use application defaults and can be overridden through the process environment when needed.

The frontend trip workflow calls `POST /api/trips/analyze/`; this composes route alternatives, ETA checkpoints, checkpoint weather, risk calculations, and route recommendation. The frontend does not contain provider credentials or fallback route/weather fixtures.

## CORS

`django-cors-headers` is included in `backend/requirements.txt`, enabled in `INSTALLED_APPS`, and its middleware runs before Django's security middleware. Install the pinned backend dependencies with `pip install -r requirements.txt` from `backend/` (or install the package directly with `pip install django-cors-headers`). Set `CORS_ALLOWED_ORIGINS` to a comma-separated list of exact frontend origins, including the scheme but no path, for example `http://localhost:5173` locally or `https://your-frontend.onrender.com` in Render. For production (`DJANGO_DEBUG=False`), the settings require at least one HTTPS origin. Add both the Render domain and any custom frontend domain if both are used. Do not use `CORS_ALLOW_ALL_ORIGINS` for production.

For backend tests, install `pip install -r requirements-dev.txt`; run checks with `python manage.py check` and tests with `python -m pytest` from `backend/`.

## Production configuration (provider-neutral)

Use a hosting platform that runs a Python WSGI service and a static frontend. The backend settings reject placeholder secrets, wildcard/missing hosts, non-HTTPS CORS origins, and SQLite when `DJANGO_DEBUG=False`. PostgreSQL can be configured with `DJANGO_DB_ENGINE=django.db.backends.postgresql`, `DJANGO_DB_NAME`, `DJANGO_DB_USER`, `DJANGO_DB_PASSWORD`, `DJANGO_DB_HOST`, and `DJANGO_DB_PORT`; alternatively set a PostgreSQL `DATABASE_URL`. Install backend requirements, including Gunicorn and Psycopg, and run from `backend/`:

```sh
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 60
```

Set `DJANGO_DEBUG=False`, a unique `DJANGO_SECRET_KEY`, explicit `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` with the HTTPS frontend origin, PostgreSQL settings, and `OPENROUTESERVICE_API_KEY` in the host's secret/environment manager. `CORS_ALLOWED_ORIGINS` must be configured before the first deploy because Django validates it during `collectstatic` too. Use the exact origin only (scheme and hostname, no path or trailing slash), for example `https://your-project.vercel.app`; do not leave the local `http://localhost:5173` example in the production service. Production mode trusts the forwarded HTTPS scheme and enforces secure cookies and HTTPS redirects. WhiteNoise serves collected static files using compressed manifest storage; it does not provide persistent storage for user uploads.

For Render, set the service root directory to `backend`, the build command to `./build.sh`, and the start command to `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 60`. Binding to `0.0.0.0:$PORT` lets Render route traffic to Gunicorn. Django adds Render's `RENDER_EXTERNAL_HOSTNAME` to `ALLOWED_HOSTS` automatically. Explicit host configuration accepts `DJANGO_ALLOWED_HOSTS` (the example-file name), Django's conventional `ALLOWED_HOSTS`, or the `ALLOW_HOSTS` alias. The executable `backend/build.sh` installs requirements, collects static files, then applies migrations.

Build the frontend with the browser-reachable API URL present at build time:

```sh
VITE_API_BASE_URL=https://api.example.com/api npm run build
```

Publish `frontend/dist/` on a static host with SPA fallback to `index.html`. Configure the actual API and frontend origins in Django; the development CORS allowlist is not suitable for production. SQLite and Django's in-memory cache are intended for local development/single-process use; production should use PostgreSQL and a shared cache if running multiple instances. Provider keys must be stored in platform secrets, not frontend build variables. Deployment remains unverified until run on the chosen host.

## Deploy the frontend to Vercel

Import the Git repository into Vercel and set **Root Directory** to `frontend`. `frontend/vercel.json` configures the Vite build (`npm run build`), publishes `dist`, and falls back to `index.html` for SPA routes. In the Vercel project settings, add this environment variable for Production (and Preview if desired):

```text
VITE_API_BASE_URL=https://<your-render-backend>.onrender.com/api
```

This value is embedded at build time and must point to the deployed Django API, including `/api`. It is a public browser URL; do not put API keys, database credentials, or other secrets in Vercel `VITE_` variables. Redeploy after changing it. In the Render backend environment, set `CORS_ALLOWED_ORIGINS` to the exact Vercel production origin, such as `https://<your-project>.vercel.app`, and include any custom frontend origin. Preview deployments use different origins, so add their exact origins only if those previews need API access. After deployment, check the browser network console and `/api/health/` endpoint.

## Neon PostgreSQL

The backend uses Django's existing PostgreSQL engine and Psycopg driver; the React client does not connect directly to the database. Initialize/link the Neon project, deploy its policy, and pull the database variables into the backend-specific env file:

```sh
npm i -g neon@latest
neon init -y --org-id <org-id> --project-id <project-id> --branch production --services postgres
neon deploy
neon env pull --file backend/.env.local
```

`neon deploy` applies the repository's `neon.ts` policy and may create a root `.env.local`. Pull the branch variables into `backend/.env.local`, then remove the root copy to keep frontend and backend configuration separate. Both env files are ignored by Git. Django loads `backend/.env.local` before `backend/.env`; process environment variables take precedence. `backend/.env.local`, `backend/.env`, and `backend/.env.example` share the same minimal variable names; use `.env.local` for local secrets and keep `.env.example` populated only with safe placeholders. Vite loads `frontend/.env.local` automatically. Keep `OPENROUTESERVICE_API_KEY` in a backend env file or the backend host's secret manager; never put it in `frontend/.env.local`.

Use Neon `DATABASE_URL` (pooled, hostname includes `-pooler`) for normal application traffic. The Django configuration detects pooled hosts, uses `CONN_MAX_AGE=0`, and disables server-side cursors for PgBouncer transaction pooling. Use Neon `DATABASE_URL_UNPOOLED` as `DATABASE_URL` when running migrations or other schema operations. The app currently has no trip-history models; PostgreSQL is configured for Django and currently stores its standard auth, admin, session, and migration tables only.

Keep `VITE_API_BASE_URL` in `frontend/.env.local` (for local development, `http://localhost:8000/api`). Keep Neon database URLs and branch variables in `backend/.env.local`. Check Neon CLI authentication and the linked branch with `neon status`; preview policy changes with `neon config plan`. Run `neon skills status --global` to check the globally installed Neon skills. The installed Neon Postgres plugin is user-level and includes the Neon MCP server and skills for all projects using that Codex profile.
