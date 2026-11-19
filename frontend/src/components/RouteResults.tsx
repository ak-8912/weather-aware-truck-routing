import { Check, Clock3, CloudOff, ShieldAlert, ShieldCheck, Wind } from 'lucide-react'
import type { Analysis, RouteAnalysis } from '../lib/api'

type Props = { analysis: Analysis; selectedRouteId: string; onSelectRoute: (id: string) => void }
const riskOrder = ['low', 'moderate', 'high', 'severe', 'no_travel', 'unavailable_weather']
const pretty = (value: string) => value.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase())
const duration = (seconds: number) => { const hours = Math.floor(seconds / 3600); const minutes = Math.round(seconds % 3600 / 60); return `${hours}h ${minutes}m` }
const fmt = (number: number) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(number)

function RouteCard({ route, analysis, selected, recommended, onClick }: { route: RouteAnalysis; analysis: Analysis; selected: boolean; recommended: boolean; onClick: () => void }) {
  const risk = route.risk_miles
  return <button type="button" className={`route-card ${selected ? 'selected' : ''}`} onClick={onClick} aria-pressed={selected}>
    <div className="route-card-head"><span className="route-index">{route.route_id.replace('route-', 'R')}</span><div className="route-title"><strong>{recommended ? 'Recommended route' : `Route ${route.route_id.replace('route-', '')}`}</strong><small>{route.safe_to_travel ? <><ShieldCheck size={12} /> Verified weather coverage</> : <><ShieldAlert size={12} /> {route.no_travel_exposure_miles > 0 ? 'No Travel exposure' : 'Weather data incomplete'}</>}</small></div>{recommended && <span className="recommended-tag"><Check size={12} /> BEST</span>}</div>
    <div className="route-stats"><div><strong>{fmt(route.distance_miles)}<small> mi</small></strong><span>Distance</span></div><div><strong>{duration(route.duration_seconds)}</strong><span>Travel time</span></div><div><strong>{route.average_risk_score == null ? '—' : route.average_risk_score.toFixed(2)}<small>/5</small></strong><span>Avg. risk</span></div></div>
    <div className="route-risk"><div className="risk-bar" aria-label="Risk miles breakdown">{riskOrder.filter((category) => (risk[category] ?? 0) > 0).map((category) => <span key={category} className={`bar-${category}`} style={{ width: `${Math.max(1, (risk[category] / route.distance_miles) * 100)}%` }} title={`${pretty(category)}: ${fmt(risk[category])} mi`} />)}</div>
      <div className="risk-breakdown">{riskOrder.map((category) => <span key={category}><i className={`dot-${category}`} />{pretty(category)} <b>{fmt(risk[category] ?? 0)}</b></span>)}</div></div>
    <div className="route-foot"><span><Wind size={13} /> Max {route.maximum_risk_level ? pretty(route.maximum_risk_level) : 'Unknown'}</span><span><CloudOff size={13} /> {route.weather_coverage_percent.toFixed(0)}% weather coverage</span></div>
    <div className="route-arrival"><Clock3 size={13} /> Arrives {new Date(route.estimated_arrival_time).toLocaleString( undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</div>
    {selected && <span className="selected-check"><Check size={13} /></span>}
    <span className="sr-only">Select {route.route_id}</span>
    <span className="route-origin-label">{analysis.trip.origin.name} to {analysis.trip.destination.name}</span>
  </button>
}

export default function RouteResults({ analysis, selectedRouteId, onSelectRoute }: Props) {
  const explanation = analysis.recommendation_explanation
  return <section className="results-section" aria-label="Route comparisons">
    <div className={`recommendation-banner ${explanation.status === 'no_safe_routes' ? 'warning' : ''}`}><span className="recommend-icon"><ShieldCheck size={18} /></span><div><strong>{explanation.status === 'no_safe_routes' ? 'No safe route found' : explanation.status === 'incomplete_weather_data' ? 'Recommendation has gaps' : 'Route recommendation'}</strong><p>{explanation.message}</p><small>{explanation.reason}</small></div></div>
    <div className="results-heading"><div><span className="eyebrow">PROVIDER ROUTE OPTIONS</span><h2>Compare routes <span>{analysis.routes.length}</span></h2></div><small>Recommendation: severe risk, high risk, average risk, travel time</small></div>
    <div className="route-list">{analysis.routes.map((route) => <RouteCard key={route.route_id} route={route} analysis={analysis} selected={selectedRouteId === route.route_id} recommended={route.route_id === analysis.recommended_route_id} onClick={() => onSelectRoute(route.route_id)} />)}</div>
    <p className="provider-note">Routes from {analysis.analysis_metadata.routing_provider}. Weather from {analysis.analysis_metadata.weather_provider}. Weather coverage is calculated across each route.</p>
  </section>
}
