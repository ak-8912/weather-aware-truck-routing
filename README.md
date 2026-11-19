# Weather-Aware Truck Routing

Trip planning for assessing weather exposure along road routes. The React frontend uses the Django API for OpenRouteService/HeiGIT truck routing and geocoding, Open-Meteo forecasts, checkpoint-level risk calculations, route comparisons, and recommendations. Provider data is requested at analysis time; the application does not invent routes or weather observations.

## Features

- Trip form with provider-backed location autocomplete, departure time, load weight, and checkpoint spacing.
- Up to three actual HGV route alternatives, distance/time comparison, weather risk miles, coverage, and recommendation explanation.
- Interactive Leaflet map with route geometry and weather checkpoint popups.
- Risk heatmap and a 0–48 hour trip timeline that filters visible checkpoint conditions by estimated arrival time.
- Missing or incomplete forecasts remain explicitly unavailable.

## Technology

- Frontend: React, strict TypeScript, Vite, TanStack Query, Leaflet/react-leaflet.
- Backend: Django REST Framework, OpenRouteService/HeiGIT routing and Pelias geocoding, Open-Meteo weather.
- Development database: SQLite. Production database configuration: PostgreSQL.

## Repository layout

```text
backend/   Django project, route/weather/risk services, API and pytest suite
frontend/  React app, API client, Leaflet components and Vitest suite
docs/      Setup, architecture, API and risk calculation documentation
```

## Development

See [docs/SETUP.md](docs/SETUP.md). The frontend runs at `http://localhost:5173`; the Django API runs at `http://localhost:8000`.

Routing and geocoding require an OpenRouteService/HeiGIT API key in `backend/.env`. Open-Meteo is public. Run `npm test` in `frontend/` for frontend interaction tests and `python -m pytest` from `backend/` for backend tests.

Run the frontend production build with `npm run build` from `frontend/`. Run `python manage.py check` from `backend/`.

See [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) for verified scope and next steps.

## Deployment

The backend supports production environment validation, Gunicorn/WSGI startup, and PostgreSQL configuration. The frontend is a static Vite build and can be published through a static hosting service. Configure the browser-visible `VITE_API_BASE_URL`, backend secret, PostgreSQL credentials, allowed hosts, HTTPS CORS origins, and provider key in the selected hosting platform. See the production section in [docs/SETUP.md](docs/SETUP.md). No deployment has been performed or claimed.

## Known limitations

- The hosted routing provider may return fewer than three distinct alternatives and limits some alternative requests by route length.
- Weather matching is performed at generated checkpoints. The 0–48 hour control filters checkpoint observations and is not an hourly corridor forecast.
- Forecast points beyond Open-Meteo's published horizon or with missing fields are reported unavailable.
- Real routing and geocoding require the provider key. A short Boston–Cambridge live check was verified; see `DEVELOPMENT_STATUS.md` for scope and remaining live cases.
- See [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) for the latest tested scope and outstanding live checks.
# weather-aware-truck-routing
