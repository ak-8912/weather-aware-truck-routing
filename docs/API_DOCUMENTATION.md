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

Provider endpoint paths and hosted restrictions were checked against the [HeiGIT migration announcement](https://ask.openrouteservice.org/t/deprecating-api-openrouteservice-org-in-favour-of-api-heigit-org/7912), the [Directions API reference](https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/), and [hosted API restrictions](https://giscience.github.io/openrouteservice/hosted-api-restrictions).
