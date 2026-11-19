# Weather-Aware Truck Routing

Trip planning for assessing weather exposure along road routes. The React frontend uses the Django API for OpenRouteService/HeiGIT truck routing and geocoding, Open-Meteo forecasts, checkpoint-level risk calculations, route comparisons, and recommendations. Provider data is requested at analysis time; the application does not invent routes or weather observations.

## Features

- Trip form with provider-backed location autocomplete, departure time, load weight, and checkpoint spacing.
- Up to three actual HGV route alternatives, distance/time comparison, weather risk miles, coverage, and recommendation explanation.
- Interactive Leaflet map with route geometry and weather checkpoint popups.
- Risk heatmap and a 0–48 hour trip timeline that filters visible checkpoint conditions by estimated arrival time.
- Missing or incomplete forecasts remain explicitly unavailable.

## Development

See [docs/SETUP.md](docs/SETUP.md). The frontend runs at `http://localhost:5173`; the Django API runs at `http://localhost:8000`.

Routing and geocoding require an OpenRouteService/HeiGIT API key in `backend/.env`. Open-Meteo is public. Run `npm test` in `frontend/` for frontend interaction tests and `python -m pytest` from `backend/` for backend tests.

See [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) for verified scope and next steps.
# weather-aware-truck-routing
