import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { analysisFixture } from './fixtures'

vi.mock('../components/RouteMap', () => ({ default: (props: { selectedRouteId: string; heatmap: boolean; forecastHour: number }) => <div data-testid="map-state">{props.selectedRouteId}|{String(props.heatmap)}|{props.forecastHour}</div> }))

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><App /></QueryClientProvider>)
}

function backendFetch() {
  return vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const url = String(input)
    if (url.includes('/health/')) return new Response(JSON.stringify({ status: 'ok', providers: { routing_configured: true, weather_provider: 'public' } }), { status: 200 })
    if (url.includes('/geocoding/search/')) {
      const query = new URL(url).searchParams.get('q') ?? ''
      const place = query.toLowerCase().includes('seattle') ? analysisFixture.trip.destination : analysisFixture.trip.origin
      return new Response(JSON.stringify({ results: [place] }), { status: 200 })
    }
    if (url.includes('/trips/analyze/')) return new Response(JSON.stringify(analysisFixture), { status: 200 })
    return new Response('{}', { status: 404 })
  })
}

beforeEach(() => { vi.stubGlobal('fetch', backendFetch()) })
afterEach(() => cleanup())

describe('trip planning and visualization controls', () => {
  it('validates that locations must be selected from provider suggestions', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(screen.getByRole('button', { name: /analyze routes/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Choose an origin from the location suggestions.')
  })

  it('uses backend suggestions and analysis, and updates route, forecast, and heatmap selections', async () => {
    const user = userEvent.setup()
    const fetchMock = backendFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderApp()

    await user.type(screen.getAllByPlaceholderText('City, state or address')[0], 'Portland')
    await user.click(await screen.findByRole('option', { name: /Portland, Oregon/i }))
    await user.type(screen.getByPlaceholderText('Where are you headed?'), 'Seattle')
    await user.click(await screen.findByRole('option', { name: /Seattle, Washington/i }))
    await user.clear(screen.getByLabelText(/load weight/i))
    await user.type(screen.getByLabelText(/load weight/i), '40000')
    await user.click(screen.getByRole('button', { name: /10mi/i }))
    expect(screen.getByRole('button', { name: /10mi/i })).toHaveAttribute('aria-pressed', 'true')
    await user.clear(screen.getByLabelText('Departure'))
    await user.type(screen.getByLabelText('Departure'), '2026-11-20T08:00')
    await user.click(screen.getByRole('button', { name: /analyze routes/i }))

    expect(await screen.findByText('Compare routes')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/trips/analyze/'))).toBe(true)
    const analysisCall = fetchMock.mock.calls.find(([url]) => String(url).includes('/trips/analyze/'))
    expect(JSON.parse(String(analysisCall?.[1]?.body))).toMatchObject({ load_weight: 40000, sampling_interval: 10 })
    expect(screen.getByTestId('map-state')).toHaveTextContent('route-1|true|48')

    const routeTwo = screen.getByRole('button', { name: /Route 2/ })
    await user.click(routeTwo)
    expect(routeTwo).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('map-state')).toHaveTextContent('route-2|true|48')
    fireEvent.change(screen.getByRole('slider', { name: /forecast horizon/i }), { target: { value: '1' } })
    expect(screen.getByTestId('map-state')).toHaveTextContent('route-2|true|1')
    expect(screen.getByText(/1 of 1 selected route checkpoints/)).toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: /heatmap/i }))
    expect(screen.getByTestId('map-state')).toHaveTextContent('route-2|false|1')
  })

  it('renders a real API error instead of replacing it with a successful analysis', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/health/')) return new Response(JSON.stringify({ status: 'ok', providers: { routing_configured: false, weather_provider: 'public' } }), { status: 200 })
      if (url.includes('/geocoding/search/')) {
        const place = new URL(url).searchParams.get('q')?.toLowerCase().includes('seattle') ? analysisFixture.trip.destination : analysisFixture.trip.origin
        return new Response(JSON.stringify({ results: [place] }), { status: 200 })
      }
      if (url.includes('/trips/analyze/')) return new Response(JSON.stringify({ error: { code: 'routing_provider_not_configured', message: 'Configure the OpenRouteService key.', details: null } }), { status: 503 })
      return new Response('{}', { status: 404 })
    }))
    const user = userEvent.setup()
    renderApp()
    await user.type(screen.getAllByPlaceholderText('City, state or address')[0], 'Portland')
    await user.click(await screen.findByRole('option', { name: /Portland, Oregon/i }))
    await user.type(screen.getByPlaceholderText('Where are you headed?'), 'Seattle')
    await user.click(await screen.findByRole('option', { name: /Seattle, Washington/i }))
    await user.click(screen.getByRole('button', { name: /analyze routes/i }))
    expect(await screen.findByText('Configure the OpenRouteService key.')).toBeInTheDocument()
  })
})
