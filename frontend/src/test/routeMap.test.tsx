import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import RouteMap from '../components/RouteMap'
import { analysisFixture } from './fixtures'

vi.mock('react-leaflet', async () => {
  const React = await import('react')
  type Handler = { click?: () => void }
  type MapLayerProps = { children?: ReactNode; eventHandlers?: Handler; positions?: number[][]; center?: number[] }
  return {
    MapContainer: ({ children }: { children?: ReactNode }) => React.createElement('div', { 'data-testid': 'leaflet-surface' }, children),
    TileLayer: () => null,
    useMap: () => ({ fitBounds: vi.fn() }),
    Polyline: ({ eventHandlers }: MapLayerProps) => React.createElement('button', { 'data-testid': 'route-line', onClick: eventHandlers?.click }, 'route'),
    Circle: () => React.createElement('div', { 'data-testid': 'heat-layer' }),
    CircleMarker: ({ children, eventHandlers }: MapLayerProps) => React.createElement('button', { 'data-testid': 'map-marker', onClick: eventHandlers?.click }, children),
    Popup: ({ children }: { children?: ReactNode }) => React.createElement('div', null, children),
  }
})

afterEach(() => cleanup())

describe('Leaflet route layer interactions', () => {
  it('selects route geometry, opens checkpoint detail, and filters risk layers by the timeline', () => {
    const onSelectRoute = vi.fn()
    const onSelectCheckpoint = vi.fn()
    const onSelectCheckpointChange = (checkpointId: string | null) => onSelectCheckpoint(checkpointId)
    const props = {
      analysis: analysisFixture,
      selectedRouteId: 'route-1',
      onSelectRoute,
      heatmap: true,
      forecastHour: 1,
      selectedCheckpoint: null,
      onSelectCheckpoint: onSelectCheckpointChange,
    }
    const view = render(<RouteMap {...props} />)

    const routeLines = screen.getAllByTestId('route-line')
    fireEvent.click(routeLines[1])
    expect(onSelectRoute).toHaveBeenCalledWith('route-2')
    expect(screen.getAllByTestId('heat-layer')).toHaveLength(1)
    const markers = screen.getAllByTestId('map-marker')
    expect(markers).toHaveLength(3)
    expect(screen.getByText('18.0 mph')).toBeInTheDocument()
    fireEvent.click(markers[0])
    expect(onSelectCheckpoint).toHaveBeenCalledWith('cp-1')

    view.rerender(<RouteMap {...props} forecastHour={48} heatmap={false} />)
    expect(screen.queryAllByTestId('heat-layer')).toHaveLength(0)
    expect(screen.getAllByTestId('map-marker')).toHaveLength(4)
  })
})
