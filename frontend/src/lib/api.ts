export type Location = { name: string; latitude: number; longitude: number; address?: Record<string, string> }
export type Checkpoint = {
  checkpoint_id: string; latitude: number; longitude: number; distance_from_origin_miles: number
  estimated_arrival_time: string; weather_timestamp: string | null; weather_data_status: 'available' | 'incomplete' | 'unavailable'
  weather_data_available: boolean; wind_speed_mph: number | null; precipitation_inches_per_hour: number | null
  snowfall_inches_per_hour: number | null; wind_risk: string | null; rain_risk: string | null; snow_risk: string | null
  risk_level: string | null; risk_score: number | null; known_no_travel_exposure: boolean
}
export type RouteAnalysis = {
  route_id: string; geometry: [number, number][]; distance_meters: number; distance_miles: number; duration_seconds: number
  risk_miles: Record<string, number>; unavailable_weather_miles: number; no_travel_exposure_miles: number
  average_risk_score: number | null; maximum_risk_level: string | null; weather_coverage_percent: number
  safe_to_travel: boolean; estimated_arrival_time: string; checkpoints: Checkpoint[]
}
export type Analysis = {
  trip: { origin: Location; destination: Location; departure_datetime: string; load_weight: number }
  routes: RouteAnalysis[]; recommended_route_id: string
  recommendation_explanation: { status: string; message: string; reason: string; no_travel_warning: boolean }
  analysis_metadata: { routing_provider: string; weather_provider: string; sampling_interval: number; weather_coverage: number }
}
type ErrorEnvelope = { error?: { code?: string; message?: string; details?: unknown } }

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try { response = await fetch(`${API_BASE}${path}`, init) }
  catch { throw new Error('Could not reach the routing service. Check that the Django API is running.') }
  const payload: unknown = await response.json().catch(() => ({}))
  if (!response.ok) {
    const envelope = payload as ErrorEnvelope
    const message = envelope.error?.message || 'The request could not be completed.'
    const details = envelope.error?.details
    const field = details && typeof details === 'object' ? Object.values(details as Record<string, unknown>).flat().find((item) => typeof item === 'string') : undefined
    throw new Error(typeof field === 'string' ? `${message} ${field}` : message)
  }
  return payload as T
}

export function searchLocations(query: string, signal?: AbortSignal): Promise<{ results: Location[] }> {
  return request(`/geocoding/search/?q=${encodeURIComponent(query)}&limit=5`, { signal })
}

export function analyzeTrip(input: {
  origin: Location; destination: Location; departure_datetime: string; load_weight: number; sampling_interval: number
}): Promise<Analysis> {
  return request('/trips/analyze/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) })
}

export function healthCheck(signal?: AbortSignal) {
  return request<{ status: string; providers: { routing_configured: boolean; weather_provider: string } }>('/health/', { signal })
}
