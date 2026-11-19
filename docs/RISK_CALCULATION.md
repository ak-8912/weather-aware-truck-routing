# Risk calculation

Risk classifications, load adjustments, route exposure metrics, and recommendation ordering will be documented when implemented in Phase 6. The weather service supplies these internal units to the risk engine:

- Wind speed: mph at 10 metres.
- Precipitation: inches per hour, using Open-Meteo's preceding-hour precipitation amount.
- Snowfall: inches per hour, using Open-Meteo's preceding-hour snowfall amount.

Each checkpoint uses the nearest forecast hour within 30 minutes of its timezone-aware ETA. Weather coverage outside the returned forecast range is `unavailable`; a row with any required measurement missing is `incomplete`. Neither status is converted to zero or treated as safe. No risk values are calculated before Phase 6.
