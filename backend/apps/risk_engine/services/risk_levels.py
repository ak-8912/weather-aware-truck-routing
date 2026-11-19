LOW = "low"
MODERATE = "moderate"
HIGH = "high"
SEVERE = "severe"
NO_TRAVEL = "no_travel"

RISK_SEVERITY = {
    LOW: 1,
    MODERATE: 2,
    HIGH: 3,
    SEVERE: 4,
    NO_TRAVEL: 5,
}
RISK_SCORE = RISK_SEVERITY.copy()

RISK_MILE_CATEGORIES = (LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL)
UNAVAILABLE_WEATHER = "unavailable_weather"
