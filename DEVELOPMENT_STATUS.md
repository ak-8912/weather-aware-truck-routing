# Development status

## Completed phases

- Phase 1: project initialization.
- Phase 2: backend foundation.
- Phase 3: routing and geocoding integrations.
- Phase 4: checkpoint generation.
- Phase 5: weather integration.
- Phase 6: risk engine and recommendation services.
- Phase 7: React trip planning frontend and API connection.
- Phase 8: Leaflet route map, checkpoint weather visualization, route comparison, risk breakdown, and forecast timeline.
- Phase 10 implementation: production settings, WSGI startup, PostgreSQL support, and deployment documentation.
- Neon setup: linked to the existing `production` branch, applied its policy (no infrastructure drift), pulled Neon environment variables, connected Django to Neon PostgreSQL, and applied Django's standard migrations.

## Current phase

- Phase 9 live backend integration is verified. Visual map QA remains pending because BrowserOS Neo is unavailable. Phase 10 configuration and documentation are complete. Neon PostgreSQL is connected and migrated; the application hosting deployment itself has not been performed.

## Implemented features

- Responsive React + TypeScript trip planning dashboard with debounced backend geocoding, timezone-aware departure input, load weight, and 10/25/50 mile checkpoint intervals.
- `POST /api/trips/analyze/` composes provider routes, ETA checkpoint generation, Open-Meteo checkpoint weather, risk calculations, risk miles, and recommendation ranking.
- Provider errors are surfaced; no route or weather data is substituted in the application workflow.
- Route comparisons display provider distance and duration, arrival, risk-mile breakdown, average and maximum risk, coverage, safety state, and recommendation explanations.
- Leaflet renders returned route geometry, selection, checkpoint weather popups, risk circles, legend, and timeline filtered between 0 and 48 elapsed hours.
- The weather normalizer accepts Open-Meteo's live `mp/h` wind unit symbol, as well as supported metric and imperial units.
- Production settings require a non-placeholder secret, explicit hosts, HTTPS CORS origins, and PostgreSQL when `DJANGO_DEBUG=False`. PostgreSQL supports component environment variables or `DATABASE_URL`.
- CORS middleware is first, followed by Django security and WhiteNoise middleware. WhiteNoise compressed manifest storage serves collected static files; production enforces trusted forwarded HTTPS, secure cookies, and HTTPS redirects.
- Neon local setup keeps database variables in `backend/.env.local` and the API URL in `frontend/.env.local`; Django loads its backend-local file without overriding shell or hosting-platform variables. Neon pooled URLs automatically disable Django persistent connections and server-side cursors for PgBouncer transaction pooling.
- Gunicorn WSGI configuration, production dependencies, frontend static build instructions, static collection, migrations, TLS/proxy settings, and environment configuration are documented. No container configuration is included.
- Vercel deployment configuration is prepared for the Vite frontend, with SPA fallback and documented `VITE_API_BASE_URL`/backend CORS settings. The Vercel project has not been deployed or connected yet.

## Files created or modified

- `backend/config/settings.py`, `backend/config/tests/test_settings.py`, `backend/requirements.txt`, `backend/Procfile`, `backend/build.sh`, and `backend/.env.example`.
- `neon.ts`, root `package.json` and `package-lock.json`, root and backend `.gitignore` files, backend/frontend `.env.local` configuration, and `docs/SETUP.md` for Neon setup guidance.
- `frontend/vercel.json` for Vercel's Vite build and SPA fallback; deployment instructions added to `docs/SETUP.md`.
- `backend/apps/weather/services/open_meteo.py` and `backend/apps/weather/tests/test_open_meteo.py` for the `mp/h` compatibility fix and regression test.
- `frontend/src/test/routeMap.test.tsx` for route-layer, checkpoint popup, and timeline-filter interactions.
- `README.md`, `docs/SETUP.md`, `docs/API_DOCUMENTATION.md`, and this status file.

## Tests and verification

- Frontend `npm run test -- --reporter=dot` — passed (7 tests for API states, validation, autocomplete, load/sampling submission, route selection, forecast slider, heatmap, checkpoint/map layer interaction, and error handling).
- Frontend `npm run build` — passed (strict TypeScript check and Vite production bundle).
- Backend `python manage.py check` — passed.
- Backend `python -m pytest` — passed (108 tests, including routing/response normalization, checkpoint/ETA behavior, all risk boundaries, load rules, recommendation ordering, Open-Meteo conversions, trip analysis, production database settings, and Neon pooler settings).
- Production-mode `manage.py check --deploy` — passed with a test-only secret, host, HTTPS CORS origin, and PostgreSQL configuration; no production database connection was made.
- Production-mode `gunicorn --check-config config.wsgi:application` — passed.
- Live Open-Meteo request on 2026-11-19 — passed for New York coordinates; received 384 hourly rows. The live response identified wind units as `mp/h`, now normalized to mph; precipitation and snowfall were returned in inches.
- Live HeiGIT geocoding and HGV routing on 2026-11-19 — Boston, MA to Cambridge, MA returned three distinct real route alternatives (4.76, 6.54, and 6.57 miles).
- Live `POST /api/trips/analyze/` composition on 2026-11-19 — returned HTTP 200 with all three live routes, two endpoint checkpoints per route at 10-mile spacing, available checkpoint weather, 100% weather coverage per route, and a backend-generated recommendation.
- Neon `production` branch check on 2026-11-20 — `neon status` confirmed project/branch; `neon config plan` and `neon deploy` reported no policy changes and Postgres as the utilized service. Five Neon variables were pulled into ignored `backend/.env.local`; `frontend/.env.local` contains only the frontend API URL. The duplicate root env file was removed.
- Live Neon PostgreSQL checks on 2026-11-20 — Django's pooled `DATABASE_URL` returned `SELECT 1`; pooler-safe settings were active. Django's standard contenttypes, auth, admin, and session migrations were applied over the direct `DATABASE_URL_UNPOOLED`, and `showmigrations` confirmed all are applied.
- Local end-to-end API check on 2026-11-20 — local health and geocoding endpoints returned HTTP 200; Boston, MA to Cambridge, MA analysis returned three live OpenRouteService alternatives and Open-Meteo weather at all checkpoints. Vite served the updated app and the local API allowed its development CORS origin.
- Neon CLI `neon skills status --global` — all seven installed Neon skills reported up to date. The user-level Codex Neon plugin contains the MCP server and applies to all projects; no duplicate project-level MCP configuration was added.
- Local Vite and Django HTTP smoke check from Phase 8 — both returned HTTP 200; health reported `routing_configured: false`.
- Static deployment configuration check — Django system check passed and WhiteNoise `collectstatic --noinput` completed with 444 assets post-processed. Render deployment itself remains unverified.
- Browser-based visual verification was not available because BrowserOS Neo was not connected. RouteMap interaction tests use mocked React-Leaflet layer components; actual Leaflet rendering was type-checked and bundled, but not inspected in a live browser.
- The Neon database branch is provisioned/configured and migrated, but the React frontend and Django API have not been deployed to an application hosting platform.

## Known issues and limitations

- Live routing and geocoding were verified for a Boston–Cambridge request. Additional locations, long-distance alternatives, and provider error cases still depend on ORS coverage, quota, and provider response.
- The hosted ORS alternatives endpoint may return fewer than three real alternatives and has a 100 km alternative-route restriction.
- Open-Meteo and weather matching across live ORS checkpoints were verified in the short-trip analysis. Long-distance routes and weather horizons beyond the tested window remain unverified live.
- The forecast map shows checkpoint observations, not a dense hourly weather corridor. The slider filters checkpoints by elapsed trip time.
- Leaflet map tiles require access to OpenStreetMap tile servers.
- Production configuration passed Django/Gunicorn checks with representative environment values. Neon PostgreSQL was tested; a target application host, TLS proxy, and static host have not been provisioned or tested.

## Remaining work

- Inspect the Leaflet experience in BrowserOS or another approved browser session.
- Exercise additional live locations, long routes, provider quota/timeouts, and out-of-forecast weather cases.
- Provision the production API and static frontend host, configure host-specific secrets/CORS/TLS, and verify the deployed app before claiming release readiness. Neon database migrations are complete.

## Next recommended action

- Complete browser-based visual QA and test long-route/forecast-boundary cases to finish Phase 9 acceptance.
