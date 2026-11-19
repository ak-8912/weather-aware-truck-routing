import { useMemo, useState, type CSSProperties } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Activity, ArrowUpRight, Cloud, CloudRain, Clock3, Layers3, MapPinned, Menu, Shield, Truck, Wind } from 'lucide-react'
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
  } })
  const apiStatus = useQuery({ queryKey: ['api-health'], queryFn: ({ signal }) => healthCheck(signal), staleTime: 30_000, retry: false })
  const chosenRoute = useMemo(() => analysis?.routes.find((route) => route.route_id === selectedRouteId), [analysis, selectedRouteId])
  const visibleCheckpoints = chosenRoute?.checkpoints.filter((checkpoint) => (Date.parse(checkpoint.estimated_arrival_time) - Date.parse(analysis!.trip.departure_datetime)) / 3_600_000 <= forecastHour + 0.01).length ?? 0

  return <div className="app-shell">
    <header className="site-header"><a className="brand" href="#top"><span className="brand-mark"><CloudRain size={20} /></span><span>weather<span className="brand-divider">/</span>haul</span></a>
      <nav aria-label="Main navigation"><a className="nav-active" href="#planner">Trip planner</a><a href="#routes">Route analysis</a><a href="#map">Weather map</a></nav>
      <div className="header-status"><span className={`status-indicator ${apiStatus.data?.status === 'ok' ? 'online' : apiStatus.isError ? 'offline' : ''}`} />{apiStatus.isLoading ? 'Connecting' : apiStatus.data?.status === 'ok' ? 'API connected' : 'API unavailable'}</div>
      <button className="mobile-menu" aria-label="Open navigation"><Menu size={19} /></button>
    </header>
    <main id="top">
      <section className="hero"><div className="hero-copy"><span className="eyebrow"><span className="hero-live" /> WEATHER INTELLIGENCE FOR THE OPEN ROAD</span><h1>Make the miles<br /><em>safer.</em></h1><p>Compare real truck routes with forecast driven risk, checkpoint by checkpoint.</p><div className="hero-providers"><span><Truck size={14} /> HGV routing</span><span><Cloud size={14} /> Hourly forecast</span><span><Shield size={14} /> Load aware risk</span></div></div>
        <div className="hero-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="hero-sun" /><div className="hero-cloud"><Cloud size={70} strokeWidth={1.2} /></div><div className="hero-road"><span /><span /><span /></div><div className="hero-truck"><Truck size={48} strokeWidth={1.3} /></div><div className="hero-weather-card"><Wind size={15} /><span>FORECAST ACTIVE</span><b>Route conditions</b></div></div>
      </section>
      <section className="planner-layout" id="planner"><aside className="planner-card"><TripForm onSubmit={(trip) => mutation.mutate(trip)} busy={mutation.isPending} />
        {mutation.error && <div className="api-error" role="alert"><strong>Trip analysis failed</strong><p>{mutation.error.message}</p><small>Check the provider configuration and try again.</small></div>}
      </aside>
        {!analysis && <section className="empty-state"><div className="empty-map-icon"><MapPinned size={28} /></div><span className="eyebrow">YOUR ROUTE WORKSPACE</span><h2>Every route has a forecast.</h2><p>Choose locations to request truck routes and compare the weather conditions expected along the way.</p><div className="empty-steps"><span><i>01</i> Enter trip details</span><span><i>02</i> Compare real routes</span><span><i>03</i> Inspect route weather</span></div><div className="empty-footer"><ArrowUpRight size={15} /> Routes and forecasts are fetched when you analyze a trip.</div></section>}
        {analysis && <div className="analysis-column">
          <div id="routes"><RouteResults analysis={analysis} selectedRouteId={selectedRouteId} onSelectRoute={(id) => { setSelectedRouteId(id); setSelectedCheckpoint(null) }} /></div>
          <section className="visual-section" id="map"><div className="visual-heading"><div><span className="eyebrow">CONDITIONS ALONG YOUR ROUTE</span><h2>Weather map</h2></div><label className="heatmap-toggle"><input type="checkbox" checked={heatmap} onChange={(event) => setHeatmap(event.target.checked)} /><span className="toggle-track"><i /></span><Layers3 size={15} /> Heatmap</label></div>
            <div className="forecast-control"><div className="forecast-heading"><div><Clock3 size={16} /><strong>Forecast timeline</strong></div><span>Departure <b>+{forecastHour}h</b></span></div><input aria-label="Forecast horizon in hours" type="range" min="0" max="48" step="1" value={forecastHour} onChange={(event) => setForecastHour(Number(event.target.value))} style={{ '--range-progress': `${forecastHour / 48 * 100}%` } as CSSProperties} /><div className="slider-labels"><span>0h · departure</span><span>24h</span><span>48h · extended forecast</span></div><small>{visibleCheckpoints} of {chosenRoute?.checkpoints.length ?? 0} selected route checkpoints fall within this departure window. Checkpoints after 48 hours are outside the displayed timeline; Open-Meteo may still cover them.</small></div>
            <RouteMap analysis={analysis} selectedRouteId={selectedRouteId} onSelectRoute={(id) => { setSelectedRouteId(id); setSelectedCheckpoint(null) }} heatmap={heatmap} forecastHour={forecastHour} selectedCheckpoint={selectedCheckpoint} onSelectCheckpoint={setSelectedCheckpoint} />
            <p className="map-disclaimer">The timeline reveals checkpoints whose estimated arrival falls within the selected hours after departure. Risk colors represent forecast conditions at those route checkpoints.</p>
          </section>
        </div>}
      </section>
      {analysis && <section className="analysis-meta"><span><Activity size={14} /> ANALYSIS SOURCES</span><p>{analysis.analysis_metadata.routing_provider} routes · {analysis.analysis_metadata.weather_provider} weather · {analysis.analysis_metadata.sampling_interval}-mile checkpoint spacing</p><span className="meta-coverage">Trip weather coverage: {analysis.analysis_metadata.weather_coverage.toFixed(1)}%</span></section>}
    </main>
    <footer className="site-footer"><span>weather<span className="brand-divider">/</span>haul <small>Route conditions, made visible.</small></span><span>Weather forecasts are estimates and do not replace official road advisories.</span><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">Map data © OpenStreetMap <ArrowUpRight size={12} /></a></footer>
  </div>
}

export default App
