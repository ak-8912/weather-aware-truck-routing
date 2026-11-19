import type { Analysis } from '../lib/api'

export const analysisFixture: Analysis = {
  trip: {
    origin: { name: 'Portland, Oregon', latitude: 45.5152, longitude: -122.6784 },
    destination: { name: 'Seattle, Washington', latitude: 47.6062, longitude: -122.3321 },
    departure_datetime: '2026-11-20T08:00:00Z', load_weight: 35000,
  },
  routes: [
    {
      route_id: 'route-1', geometry: [[-122.6784, 45.5152], [-122.3321, 47.6062]], distance_meters: 280000,
      distance_miles: 174, duration_seconds: 14400, risk_miles: { low: 100, moderate: 74, high: 0, severe: 0, no_travel: 0, unavailable_weather: 0 },
      unavailable_weather_miles: 0, no_travel_exposure_miles: 0, average_risk_score: 1.42, maximum_risk_level: 'moderate',
      weather_coverage_percent: 100, safe_to_travel: true, estimated_arrival_time: '2026-11-20T12:00:00Z', checkpoints: [
        { checkpoint_id: 'cp-1', latitude: 45.5152, longitude: -122.6784, distance_from_origin_miles: 0, estimated_arrival_time: '2026-11-20T08:00:00Z', weather_timestamp: '2026-11-20T08:00:00Z', weather_data_status: 'available', weather_data_available: true, wind_speed_mph: 18, precipitation_inches_per_hour: 0, snowfall_inches_per_hour: 0, wind_risk: 'low', rain_risk: 'low', snow_risk: 'low', risk_level: 'low', risk_score: 1, known_no_travel_exposure: false },
        { checkpoint_id: 'cp-2', latitude: 47.6062, longitude: -122.3321, distance_from_origin_miles: 174, estimated_arrival_time: '2026-11-20T20:00:00Z', weather_timestamp: '2026-11-20T20:00:00Z', weather_data_status: 'available', weather_data_available: true, wind_speed_mph: 30, precipitation_inches_per_hour: 0.1, snowfall_inches_per_hour: 0, wind_risk: 'moderate', rain_risk: 'moderate', snow_risk: 'low', risk_level: 'moderate', risk_score: 2, known_no_travel_exposure: false },
      ],
    },
    {
      route_id: 'route-2', geometry: [[-122.6784, 45.5152], [-122.3321, 47.6061]], distance_meters: 300000,
      distance_miles: 186, duration_seconds: 16200, risk_miles: { low: 181, moderate: 0, high: 5, severe: 0, no_travel: 0, unavailable_weather: 0 },
      unavailable_weather_miles: 0, no_travel_exposure_miles: 0, average_risk_score: 1.1, maximum_risk_level: 'high',
      weather_coverage_percent: 100, safe_to_travel: true, estimated_arrival_time: '2026-11-20T12:30:00Z', checkpoints: [
        { checkpoint_id: 'cp-3', latitude: 45.5152, longitude: -122.6784, distance_from_origin_miles: 0, estimated_arrival_time: '2026-11-20T08:00:00Z', weather_timestamp: '2026-11-20T08:00:00Z', weather_data_status: 'available', weather_data_available: true, wind_speed_mph: 17, precipitation_inches_per_hour: 0, snowfall_inches_per_hour: 0, wind_risk: 'low', rain_risk: 'low', snow_risk: 'low', risk_level: 'low', risk_score: 1, known_no_travel_exposure: false },
      ],
    },
  ],
  recommended_route_id: 'route-1',
  recommendation_explanation: { status: 'recommended', message: 'Route ranks first.', reason: 'Lowest risk.', no_travel_warning: false },
  analysis_metadata: { routing_provider: 'OpenRouteService', weather_provider: 'Open-Meteo', sampling_interval: 25, weather_coverage: 100 },
}
