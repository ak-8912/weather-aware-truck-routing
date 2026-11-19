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

Run backend checks with `python manage.py check` and backend tests with `python -m pytest` from `backend/`.
