import { useMemo, useState, type CSSProperties } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Activity, ArrowUpRight, Clock3, Layers3, Shield, Truck } from 'lucide-react'
import TripForm, { type TripInput } from './components/TripForm'
import RouteMap from './components/RouteMap'
import RouteResults from './components/RouteResults'
import { analyzeTrip, healthCheck, type Analysis } from './lib/api'

function App() {
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState('')
  const [forecastHour, setForecastHour] = useState(48)
  const [heatmap, setHeatmap] = useState(true)
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<string | null>(null)
  const mutation = useMutation({ mutationFn: (trip: TripInput) => analyzeTrip(trip), onSuccess: (result) => {
      setAnalysis(result); setSelectedRouteId(result.recommended_route_id); setForecastHour(48); setSelectedCheckpoint(null)
      window.setTimeout(() => document.getElementById('route-analysis')?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }), 0)
  } })
  const apiStatus = useQuery({ queryKey: ['api-health'], queryFn: ({ signal }) => healthCheck(signal), staleTime: 30_000, retry: false })
  const chosenRoute = useMemo(() => analysis?.routes.find((route) => route.route_id === selectedRouteId), [analysis, selectedRouteId])
  const visibleCheckpoints = chosenRoute?.checkpoints.filter((checkpoint) => (Date.parse(checkpoint.estimated_arrival_time) - Date.parse(analysis!.trip.departure_datetime)) / 3_600_000 <= forecastHour + 0.01).length ?? 0

  return <div className="app-shell">
    <header className="site-header"><a className="brand" href="#top" aria-label="Weather aware truck routing home"><span className="brand-mark"><Truck size={18} strokeWidth={2.2} /></span><span>WATR</span></a>
      <div className="header-status"><span className={`status-indicator ${apiStatus.data?.status === 'ok' ? 'online' : apiStatus.isError ? 'offline' : ''}`} />{apiStatus.isLoading ? 'Connecting' : apiStatus.data?.status === 'ok' ? 'API connected' : 'API unavailable'}</div>
    </header>
    <main id="top">
      <section className="hero"><div className="hero-copy"><span className="eyebrow"><span className="hero-live" /> WEATHER INTELLIGENCE FOR THE OPEN ROAD</span><h1>Make the miles<br /><em>safer.</em></h1><p>Compare real truck routes with forecast driven risk, checkpoint by checkpoint.</p><div className="hero-providers"><span>HGV routing</span><span>Hourly forecast</span><span><Shield size={14} /> Load aware risk</span></div>
          <div className="hero-visual" aria-hidden="true"><svg viewBox="0 0 620 185" preserveAspectRatio="none"><path className="hero-contour" d="M0 122 C90 42 140 169 231 93 S373 45 432 105 533 160 620 72" /><path className="hero-contour" d="M0 150 C90 70 140 197 231 121 S373 73 432 133 533 188 620 100" /><path className="hero-route-line" d="M17 80 C103 45 153 168 248 91 S374 51 435 109 526 148 601 83" /></svg><i className="hero-route-point point-start" /><i className="hero-route-point point-end" /><div className="hero-visual-caption"><span>ONE VIEW FOR THE ROAD AHEAD</span><strong>Routes, weather, risk — together.</strong></div><div className="hero-visual-badge"><span /><b>Plan with confidence</b></div></div>
        </div>
        <aside className="planner-card hero-planner" id="planner"><TripForm onSubmit={(trip) => mutation.mutate(trip)} busy={mutation.isPending} />
          {mutation.error && <div className="api-error" role="alert"><strong>Trip analysis failed</strong><p>{mutation.error.message}</p><small>Check the provider configuration and try again.</small></div>}
        </aside>
      </section>
      {analysis && <section className="analysis-workspace" id="route-analysis"><div className="analysis-controls" id="routes">
        <RouteResults analysis={analysis} selectedRouteId={selectedRouteId} onSelectRoute={(id) => { setSelectedRouteId(id); setSelectedCheckpoint(null) }} />
        <div className="forecast-control"><div className="forecast-heading"><div><Clock3 size={16} /><strong>Forecast timeline</strong></div><span>Departure <b>+{forecastHour}h</b></span></div><input aria-label="Forecast horizon in hours" type="range" min="0" max="48" step="1" value={forecastHour} onChange={(event) => setForecastHour(Number(event.target.value))} style={{ '--range-progress': `${forecastHour / 48 * 100}%` } as CSSProperties} /><div className="slider-labels"><span>0h · departure</span><span>24h</span><span>48h · extended forecast</span></div><small>{visibleCheckpoints} of {chosenRoute?.checkpoints.length ?? 0} selected route checkpoints fall within this departure window. Checkpoints after 48 hours are outside the displayed timeline; Open-Meteo may still cover them.</small></div>
      </div><section className="visual-section" id="map"><div className="visual-heading"><div><span className="eyebrow">CONDITIONS ALONG YOUR ROUTE</span><h2>Weather map</h2></div><label className="heatmap-toggle"><input type="checkbox" checked={heatmap} onChange={(event) => setHeatmap(event.target.checked)} /><span className="toggle-track"><i /></span><Layers3 size={15} /> Heatmap</label></div>
        <RouteMap analysis={analysis} selectedRouteId={selectedRouteId} onSelectRoute={(id) => { setSelectedRouteId(id); setSelectedCheckpoint(null) }} heatmap={heatmap} forecastHour={forecastHour} selectedCheckpoint={selectedCheckpoint} onSelectCheckpoint={setSelectedCheckpoint} />
        <p className="map-disclaimer">The timeline reveals checkpoints whose estimated arrival falls within the selected hours after departure. Risk colors represent forecast conditions at those route checkpoints.</p>
      </section></section>}
      {analysis && <section className="analysis-meta"><span><Activity size={14} /> ANALYSIS SOURCES</span><p>{analysis.analysis_metadata.routing_provider} routes · {analysis.analysis_metadata.weather_provider} weather · {analysis.analysis_metadata.sampling_interval}-mile checkpoint spacing</p><span className="meta-coverage">Trip weather coverage: {analysis.analysis_metadata.weather_coverage.toFixed(1)}%</span></section>}
    </main>
    <footer className="site-footer"><span>Weather aware truck routing <small>Route conditions, made visible.</small></span><span>Weather forecasts are estimates and do not replace official road advisories.</span><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">Map data © OpenStreetMap <ArrowUpRight size={12} /></a></footer>
  </div>
}

export default App
