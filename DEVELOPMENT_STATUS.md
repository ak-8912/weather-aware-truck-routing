# Development status

## Completed phases

- Phase 1: project initialization.
- Phase 2: backend foundation.
- Phase 3: routing and geocoding integrations.
- Phase 4: checkpoint generation.
- Phase 5: weather integration.

## Current phase

- Phase 6: risk engine.

## Implemented features

- React + TypeScript + Vite frontend scaffold with a landing screen, favicon, Tailwind CSS v4, and shadcn/ui configuration.
- Django project and four app packages with DRF, CORS, dotenv, SQLite, JSON logging, a validated health endpoint, and a common DRF error envelope.
- OpenRouteService provider abstraction and hosted integration for HGV directions and Pelias geocoding; route response normalization, geometry deduplication, geocoding cache, input/output serializers, and provider error mapping.
- Route alternative and geocoding API endpoints with explicit notices when fewer than three real alternatives are available.
- Checkpoint generation along route geometry at 10-, 25-, and 50-mile intervals, with interpolated coordinates, cumulative distances, endpoint handling, route-proportional ETAs, and timezone-aware departure validation.
- Open-Meteo hourly forecast provider with batched multi-location requests, 30-minute cache, timezone-safe UTC timestamps, internal mph/inches normalization, and explicit unavailable/incomplete checkpoint weather states.
- Nearest-hour weather matching within 30 minutes of each checkpoint ETA; missing forecasts or measurements remain unavailable rather than becoming zero/safe values.
- Environment examples, pytest configuration, initial documentation, and the planned source directory structure.

## Files created or modified

- Frontend application/config files and npm lockfile under `frontend/`.
- Django project, app packages, health serializer/view/URL, API exception handler, JSON log formatter, and pytest config under `backend/`.
- Routing provider/service, route processor, routing/geocoding serializers, views, URLs, and provider/API/processor tests under `backend/apps/routing/`.
- Route checkpoint generator and checkpoint/ETA boundary tests under `backend/apps/routing/services/` and `backend/apps/routing/tests/`.
- Open-Meteo provider abstraction, forecast normalization, checkpoint weather matching, and unit/error/coverage tests under `backend/apps/weather/services/` and `backend/apps/weather/tests/`.
- Open-Meteo configuration values and timeout/cache settings in `backend/config/settings.py` and `backend/.env.example`.
- Updated architecture, API, risk-input, and setup documentation for checkpoints and weather integration.
- Updated ORS endpoint configuration and `.env.example`; expanded API, architecture, and setup documentation.
- Initial docs, root README, `.gitignore`, and this status file.

## Tests and verification

- `npm install` — passed (141 packages; 0 reported vulnerabilities).
- `npm run build` — passed (TypeScript check and Vite production build).
- `python manage.py check` — passed.
- `python manage.py migrate --noinput` — passed (local SQLite initialized).
- `python -m pytest` in `backend/` — passed (28 total tests: health/error envelope, routing/geocoding endpoints, ORS request/error handling, route normalization/deduplication, and checkpoint generation/ETA/interpolation).
- `python manage.py check` — passed after Phase 2 changes.
- Development server smoke check — frontend and backend both returned HTTP 200.
- `python manage.py check` — passed after Phase 3 and Phase 4 changes.
- `python manage.py check` — passed after Phase 5 changes.
- `python -m pytest` in `backend/` — passed (43 total tests, including batched Open-Meteo requests, caching, measurement conversions, forecast time matching, timezone handling, and incomplete/out-of-coverage weather cases).
- External API responses are mocked in tests. A live-provider check was not run because no ORS API key is configured.

## Known issues

- OpenRouteService/HeiGIT API key is not configured; live routing and geocoding verification requires a key in `backend/.env`.
- Hosted ORS alternative route requests are limited to routes up to 100 km; when that specific limit is returned, the service retries for the provider's primary route only.
- Open-Meteo's general forecast API returns up to 16 forecast days. Later checkpoint ETAs are explicitly marked unavailable.
- Live weather API connectivity was not exercised; provider responses were mocked in the automated tests.
- No Git repository was present in the supplied directory.

## Remaining work

- Phases 1–5 are complete.
- Phase 6 has not started; waiting for the user's instruction to continue.

## Next recommended action

- Begin Phase 6 after the user asks to continue.
