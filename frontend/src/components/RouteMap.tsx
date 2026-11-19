import { Fragment, useEffect } from 'react'
import { Circle, CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import type { Analysis, Checkpoint, RouteAnalysis } from '../lib/api'

type Props = { analysis: Analysis; selectedRouteId: string; onSelectRoute: (id: string) => void; heatmap: boolean; forecastHour: number; selectedCheckpoint: string | null; onSelectCheckpoint: (id: string | null) => void }
const riskColors: Record<string, string> = { low: '#42b883', moderate: '#f4c95d', high: '#f29b4b', severe: '#ef6b55', no_travel: '#d9485f' }
const colorFor = (level: string | null) => level ? riskColors[level] ?? '#8c9aa9' : '#8c9aa9'
const point = (checkpoint: Checkpoint): [number, number] => [checkpoint.latitude, checkpoint.longitude]

function Viewport({ routes }: { routes: RouteAnalysis[] }) {
  const map = useMap()
  useEffect(() => {
    const points = routes.flatMap((route) => route.geometry.map(([longitude, latitude]) => L.latLng(latitude, longitude)))
    if (points.length) map.fitBounds(L.latLngBounds(points), { padding: [36, 36], maxZoom: 8 })
  }, [map, routes])
  return null
}

function elapsedHours(checkpoint: Checkpoint, departure: string) {
  return (Date.parse(checkpoint.estimated_arrival_time) - Date.parse(departure)) / 3_600_000
}

export default function RouteMap({ analysis, selectedRouteId, onSelectRoute, heatmap, forecastHour, selectedCheckpoint, onSelectCheckpoint }: Props) {
  const selected = analysis.routes.find((route) => route.route_id === selectedRouteId) ?? analysis.routes[0]
  return <div className="map-frame">
    <div className="map-topline"><div><span className="live-pulse" /> ROUTE WEATHER MAP</div><span>{analysis.analysis_metadata.sampling_interval} mi checkpoints</span></div>
    <MapContainer center={[39.5, -98.35]} zoom={4} scrollWheelZoom className="leaflet-map">
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <Viewport routes={analysis.routes} />
      {analysis.routes.map((route) => {
        const active = route.route_id === selectedRouteId
        const coordinates = route.geometry.map(([longitude, latitude]) => [latitude, longitude] as [number, number])
        const routeColor = colorFor(route.maximum_risk_level)
        return <Polyline key={route.route_id} positions={coordinates} pathOptions={{ color: routeColor, weight: active ? 6 : 4, opacity: active ? 0.95 : 0.45, dashArray: active ? undefined : '8 8' }} eventHandlers={{ click: () => onSelectRoute(route.route_id) }} />
      })}
      {selected && selected.checkpoints.map((checkpoint) => {
        const hours = elapsedHours(checkpoint, analysis.trip.departure_datetime)
        const visible = hours <= forecastHour + 0.01
        if (!visible) return null
        const color = colorFor(checkpoint.risk_level)
        const chosen = selectedCheckpoint === checkpoint.checkpoint_id
        return <Fragment key={checkpoint.checkpoint_id}>
          {heatmap && visible && <Circle center={point(checkpoint)} radius={Math.min(10000, Math.max(2800, analysis.analysis_metadata.sampling_interval * 170))} pathOptions={{ color, fillColor: color, fillOpacity: 0.14, weight: 1, opacity: 0.35 }} />}
          <CircleMarker center={point(checkpoint)} radius={chosen ? 9 : 6} pathOptions={{ color: '#fff', weight: 2, fillColor: color, fillOpacity: 0.95 }} eventHandlers={{ click: () => onSelectCheckpoint(checkpoint.checkpoint_id) }}>
            <Popup><div className="checkpoint-popup"><strong>{checkpoint.distance_from_origin_miles.toFixed(1)} mi from origin</strong><small>{new Date(checkpoint.estimated_arrival_time).toLocaleString()}</small>
              <span className={`risk-pill risk-${checkpoint.risk_level ?? 'unavailable'}`}>{checkpoint.risk_level?.replace('_', ' ') ?? checkpoint.weather_data_status}</span>
              <div className="popup-weather"><span>Wind <b>{checkpoint.wind_speed_mph == null ? 'Unavailable' : `${checkpoint.wind_speed_mph.toFixed(1)} mph`}</b></span><span>Rain <b>{checkpoint.precipitation_inches_per_hour == null ? 'Unavailable' : `${checkpoint.precipitation_inches_per_hour.toFixed(2)} in/hr`}</b></span><span>Snow <b>{checkpoint.snowfall_inches_per_hour == null ? 'Unavailable' : `${checkpoint.snowfall_inches_per_hour.toFixed(2)} in/hr`}</b></span></div>
              <small>Forecast: {checkpoint.weather_timestamp ? new Date(checkpoint.weather_timestamp).toLocaleString() : 'unavailable'} · {checkpoint.weather_data_status}</small>
            </div></Popup>
          </CircleMarker>
        </Fragment>
      })}
      {selected && selected.geometry.length > 0 && <><CircleMarker center={[selected.geometry[0][1], selected.geometry[0][0]]} radius={7} pathOptions={{ color: '#fff', fillColor: '#218b78', fillOpacity: 1, weight: 2 }}><Popup>{analysis.trip.origin.name || 'Origin'}</Popup></CircleMarker><CircleMarker center={[selected.geometry.at(-1)![1], selected.geometry.at(-1)![0]]} radius={7} pathOptions={{ color: '#fff', fillColor: '#344c78', fillOpacity: 1, weight: 2 }}><Popup>{analysis.trip.destination.name || 'Destination'}</Popup></CircleMarker></>}
    </MapContainer>
    <div className="map-legend"><strong>{heatmap ? 'Weather risk' : 'Route risk'}</strong>{Object.entries(riskColors).map(([level, color]) => <span key={level}><i style={{ backgroundColor: color }} />{level.replace('_', ' ')}</span>)}<span><i className="legend-muted" />Unavailable</span></div>
  </div>
}
