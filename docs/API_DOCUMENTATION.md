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
