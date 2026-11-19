import { afterEach, describe, expect, it, vi } from 'vitest'
import { analyzeTrip, searchLocations } from '../lib/api'
import { analysisFixture } from './fixtures'

afterEach(() => vi.unstubAllGlobals())

describe('backend API client', () => {
  it('requests geocoding suggestions from the Django endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ results: [{ name: 'Portland', latitude: 45, longitude: -122 }] }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const result = await searchLocations('Portland, OR')
    expect(result.results[0].name).toBe('Portland')
    expect(fetchMock.mock.calls[0][0]).toContain('/geocoding/search/?q=Portland%2C%20OR')
  })

  it('posts trip parameters and returns the backend analysis without local calculations', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(analysisFixture), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const trip = { origin: analysisFixture.trip.origin, destination: analysisFixture.trip.destination, departure_datetime: '2026-11-20T08:00:00Z', load_weight: 35000, sampling_interval: 25 }
    const result = await analyzeTrip(trip)
    const request = fetchMock.mock.calls[0][1] as RequestInit
    expect(fetchMock.mock.calls[0][0]).toContain('/trips/analyze/')
    expect(JSON.parse(String(request.body))).toEqual(trip)
    expect(result.recommended_route_id).toBe('route-1')
    expect(result.routes[0].checkpoints[1].wind_speed_mph).toBe(30)
  })

  it('surfaces structured provider errors to the caller', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: 'routing_provider_not_configured', message: 'Routing is not configured.', details: null } }), { status: 503 })))
    await expect(searchLocations('Portland')).rejects.toThrow('Routing is not configured.')
  })
})
