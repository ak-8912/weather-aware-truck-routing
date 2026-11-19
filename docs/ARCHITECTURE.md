# Architecture

The repository is a Vite/React TypeScript frontend and a Django REST Framework backend. Browser requests use the API base URL in `frontend/.env`; provider credentials remain in backend environment variables. SQLite is configured for local development. Routing, geocoding, weather, checkpoint generation, and risk analysis will be added in their respective backend apps in later phases.
