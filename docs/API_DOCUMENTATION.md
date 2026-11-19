# API documentation

## `GET /api/health/`

Returns backend status, application version, and whether the routing provider key is configured. No credentials are returned.

Example: `{"status":"ok","version":"0.1.0","providers":{"routing_configured":false}}`
