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

Health endpoint: `http://localhost:8000/api/health/`. Add an OpenRouteService API key to `backend/.env` before routing/geocoding are implemented. Open-Meteo access is public and needs no key for this workflow.
