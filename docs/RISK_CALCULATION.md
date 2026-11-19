# Risk calculation

All risk classifications and recommendation calculations run in Django under `apps/risk_engine/services/`. Values use the weather service's normalized units:

- Wind speed at 10 metres: mph.
- Precipitation: inches per hour.
- Snowfall: inches per hour.
- Load weight: pounds.

## Individual weather classifications

Boundary convention: lower thresholds enter the higher category. Rain at exactly 1.00 in/hr and snow at exactly 3.00 in/hr remain Severe; values above those inclusive maxima are No Travel.

| Measure | Low | Moderate | High | Severe | No Travel |
| --- | --- | --- | --- | --- | --- |
| Wind (mph) | `<25` | `>=25 and <35` | `>=35 and <45` | `>=45 and <55` | `>=55` |
| Rain (in/hr) | `<0.10` | `>=0.10 and <0.25` | `>=0.25 and <0.50` | `>=0.50 and <=1.00` | `>1.00` |
| Snow (in/hr) | `<0.5` | `>=0.5 and <1.0` | `>=1.0 and <2.0` | `>=2.0 and <=3.0` | `>3.0` |

Severity ordering is `Low=1`, `Moderate=2`, `High=3`, `Severe=4`, `No Travel=5`. Base weather risk is the most severe observed wind, rain, or snow classification.

## Load-adjusted wind rules

These rules change wind risk only; they do not adjust rain or snow risk.

- Wind `>=55 mph`: No Travel for every load.
- Wind `>=45 and <55 mph` with load `>30,000 lb`: No Travel.
- Wind `>=35 and <45 mph` with load `>40,000 lb`: Severe.
- Otherwise, retain the individual wind classification.

The final checkpoint risk is the more severe of complete base weather risk and load-adjusted wind risk. Individual wind, rain, snow, base weather, and load-adjusted wind classifications are retained in the checkpoint result. Invalid or negative measurements and loads are rejected.

## Missing weather measurements

A checkpoint is risk-classifiable only when wind, precipitation, and snowfall are all present and the weather service reports complete coverage. Missing data is never assigned Low. Incomplete segments accrue unavailable-weather miles and are excluded from average risk and weather coverage.

If an available measurement independently establishes No Travel (for example, wind at or above 55 mph) while another measurement is missing, the segment remains unavailable for coverage and average-risk accounting, while the known No Travel exposure is separately retained. This preserves both facts without presenting missing miles as safe.

## Route risk miles and average risk

Checkpoint risk is assigned to the portion of route closest to that checkpoint. Boundaries between adjacent checkpoints are placed at the midpoint of their cumulative route distances. The first and last checkpoints own their terminal half-segments. This accounts for the full provider-reported route distance, including its final segment, and is used consistently for every route.

Risk miles are accumulated separately for Low, Moderate, High, Severe, No Travel, and unavailable weather. The five classified categories plus unavailable-weather miles partition the route's distance. Known No Travel exposure on an otherwise incomplete segment is additionally exposed as `known_no_travel_exposure_miles` / `no_travel_exposure_miles`; that known hazard may overlap unavailable-weather miles.

Average risk is distance-weighted over complete weather segments only, using the severity scores above (including No Travel=5). It is `null` when no route miles have complete weather. Weather coverage is the percentage of total route miles with complete measurements. A route is marked safe to travel by this weather analysis only when coverage is complete and there is no known No Travel exposure.

## Route recommendation

Known No Travel exposure is a safety gate: a route with that exposure cannot outrank an alternative without it. If all available routes have No Travel exposure, the highest-ranked option is identified as the least hazardous available, with a warning that none is suitable for travel.

Within the eligible set, routes are compared lexicographically and in this exact order:

1. Fewest Severe miles.
2. Fewest High-risk miles.
3. Lowest distance-weighted average risk.
4. Shortest travel time.

No weighted score is used to change that priority. Missing weather never contributes Low-risk miles or a low average score. When any route has incomplete weather coverage, the result is marked as an incomplete comparison, the coverage of each route is disclosed, and the selected route is not labeled safe solely on incomplete data.
