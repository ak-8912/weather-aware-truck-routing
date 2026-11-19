from apps.risk_engine.services.risk_levels import HIGH, NO_TRAVEL, SEVERE


def load_adjusted_wind_risk(wind_speed_mph: float, load_weight_lb: float, base_wind_risk: str) -> str:
    """Apply the assessment's extra wind rules for heavier loads only."""
    if wind_speed_mph >= 55:
        return NO_TRAVEL
    if 45 <= wind_speed_mph < 55 and load_weight_lb > 30_000:
        return NO_TRAVEL
    if 35 <= wind_speed_mph < 45 and load_weight_lb > 40_000:
        return SEVERE
    return base_wind_risk
