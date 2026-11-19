# API documentation

## `GET /api/health/`

Returns backend status, application version, and whether the routing provider key is configured. No credentials are returned.

Example: `{"status":"ok","version":"0.1.0","providers":{"routing_configured":false,"weather_provider":"public"}}`

Provider status reports only whether the routing credential is configured; it never includes the credential itself. The public Open-Meteo forecast endpoint is reported as `weather_provider: "public"`.

## API error shape

DRF errors use a stable JSON envelope. Validation errors include field details:

```json
{
  "error": {
    "code": "invalid",
    "message": "The request could not be processed.",
    "details": {"field": ["This field is required."]}
  }
}
```

## `GET /api/geocoding/search/?q=Boston&limit=5`

Searches OpenRouteService's hosted Pelias geocoder. `q` must contain 2–160 characters; `limit` is optional and ranges from 1 to 5. Results contain a display name, latitude, longitude, and address details. Empty results return `{"results": []}`. Successful searches are cached for one hour.

## `POST /api/routes/`

Requests up to three route options from the external routing provider. Coordinates are WGS84 decimal degrees; the provider request uses `[longitude, latitude]` order. The selected `driving-hgv` profile is a provider routing mode, not a guarantee of legal truck access, bridge clearance, or weight compliance.

```json
{
  "origin": {"name": "New York", "latitude": 40.7128, "longitude": -74.006},
  "destination": {"name": "Boston", "latitude": 42.3601, "longitude": -71.0589}
}
```

The response contains only unique routes returned by the provider. Route geometry coordinates remain `[longitude, latitude]`; route distance is in meters and duration is in seconds. If fewer than three unique routes are returned, `alternatives_notice` explains the shortfall. The hosted service restricts alternative-route calculations to routes up to 100 km. If it rejects alternatives specifically due to that limit, the backend retries for the primary route only.

The backend checkpoint generator runs as an internal service rather than a standalone public endpoint. `POST /api/trips/analyze/` calls it for each provider route using a timezone-aware departure timestamp and supported sampling interval (10, 25, or 50 miles), returning checkpoint IDs, coordinates, cumulative distance, and ETA in the route analysis.

Hourly weather forecasts are retrieved by an internal service. Open-Meteo supplies wind speed at 10 m, preceding-hour precipitation, and snowfall. The service normalizes values to mph and inches/hour and attaches the closest hourly row within 30 minutes of checkpoint ETA. Forecast times outside Open-Meteo coverage or missing required measurements are labeled unavailable/incomplete. Live verification on 2026-11-19 confirmed the API returns the wind unit symbol `mp/h`; the normalizer accepts it as miles per hour.

The requested variables and units follow the [Open-Meteo Forecast API documentation](https://open-meteo.com/en/docs): hourly wind speed supports mph, precipitation/snowfall support inch units, and the general forecast endpoint supports up to 16 forecast days.

## `POST /api/trips/analyze/`

Composes provider routes, ETA checkpoints, hourly checkpoint weather, risk calculations, risk miles, and the recommendation service for a trip. The frontend requires locations to be chosen from the provider-backed geocoding suggestions. Departure time must be timezone aware; supported checkpoint intervals are 10, 25, and 50 miles; load weight is in pounds.

```json
{
  "origin": {"name": "New York", "latitude": 40.7128, "longitude": -74.006},
  "destination": {"name": "Boston", "latitude": 42.3601, "longitude": -71.0589},
  "departure_datetime": "2026-11-20T08:00:00-05:00",
  "load_weight": 35000,
  "sampling_interval": 25
}
```

The response contains `trip`, `routes`, `recommended_route_id`, `recommendation_explanation`, and `analysis_metadata`. Every route includes its provider `geometry` (`[longitude, latitude]`), distance/duration, full enriched `checkpoints`, risk miles, weather coverage, safety state, and timezone-aware arrival. Checkpoints include measured wind, precipitation and snowfall values (or `null`), forecast timestamp/status, individual and combined risk classifications, and ETA. No Travel exposure and unavailable weather remain distinct. Recommendation ranking and incompleteness rules are documented in [RISK_CALCULATION.md](RISK_CALCULATION.md).

Response shape (values below are field descriptions, not a recorded trip):

```text
{
  "trip": {"origin": {}, "destination": {}, "departure_datetime": "ISO-8601", "load_weight": 0},
  "routes": [{
    "route_id": "provider route ID",
    "geometry": [[longitude, latitude], ...],
    "distance_meters": 0,
    "duration_seconds": 0,
    "risk_miles": {"low": 0, "moderate": 0, "high": 0, "severe": 0, "no_travel": 0, "unavailable_weather": 0},
    "weather_coverage_percent": 0,
    "checkpoints": [{
      "estimated_arrival_time": "ISO-8601",
      "wind_speed_mph": null,
      "precipitation_inches_per_hour": null,
      "snowfall_inches_per_hour": null,
      "weather_data_status": "unavailable"
    }]
  }],
  "recommended_route_id": "provider route ID",
  "recommendation_explanation": {},
  "analysis_metadata": {"routing_provider": "OpenRouteService", "weather_provider": "Open-Meteo"}
}
```

The endpoint returns structured validation errors for invalid locations, load weights, times, and sampling intervals. Provider configuration, timeout, rate-limit, invalid-response, and no-route failures propagate as API errors and are not replaced with fabricated analysis data.

## Risk and recommendation services

Checkpoint and route risk calculations and route recommendation are implemented as backend services, documented in [RISK_CALCULATION.md](RISK_CALCULATION.md), and composed by `POST /api/trips/analyze/`.

Provider endpoint paths and hosted restrictions were checked against the [HeiGIT migration announcement](https://ask.openrouteservice.org/t/deprecating-api-openrouteservice-org-in-favour-of-api-heigit-org/7912), the [Directions API reference](https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/), and [hosted API restrictions](https://giscience.github.io/openrouteservice/hosted-api-restrictions).
