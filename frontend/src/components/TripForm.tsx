import { useState, type FormEvent } from 'react'
import { ArrowDown, ArrowUp, CalendarClock, Scale, Route, ArrowRight } from 'lucide-react'
import type { Location } from '../lib/api'
import LocationField from './LocationField'

export type TripInput = { origin: Location; destination: Location; departure_datetime: string; load_weight: number; sampling_interval: number }
type Props = { onSubmit: (trip: TripInput) => void; busy: boolean }

function localDateTimeValue() {
  const now = new Date(Date.now() + 30 * 60_000)
  now.setMinutes(Math.ceil(now.getMinutes() / 15) * 15, 0, 0)
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
}

export default function TripForm({ onSubmit, busy }: Props) {
  const [origin, setOrigin] = useState<Location | null>(null)
  const [destination, setDestination] = useState<Location | null>(null)
  const [departure, setDeparture] = useState(localDateTimeValue)
  const [weight, setWeight] = useState('35000')
  const [interval, setInterval] = useState(25)
  const [error, setError] = useState('')
  const submit = (event: FormEvent) => {
    event.preventDefault(); setError('')
    const pounds = Number(weight)
    if (!origin) return setError('Choose an origin from the location suggestions.')
    if (!destination) return setError('Choose a destination from the location suggestions.')
    if (origin.latitude === destination.latitude && origin.longitude === destination.longitude) return setError('Origin and destination must be different.')
    if (!departure || Number.isNaN(Date.parse(departure))) return setError('Choose a valid departure date and time.')
    if (!Number.isFinite(pounds) || pounds < 0 || pounds > 200000) return setError('Load weight must be between 0 and 200,000 lb.')
    onSubmit({ origin, destination, departure_datetime: new Date(departure).toISOString(), load_weight: pounds, sampling_interval: interval })
  }
  return <form className="trip-form" onSubmit={submit}>
    <div className="form-section-title"><span className="section-icon"><Route size={17} /></span><div><strong>Plan a trip</strong><small>Get route specific weather risk before you roll.</small></div></div>
    <div className="location-stack"><LocationField label="Origin" value={origin} onChange={setOrigin} placeholder="City, state or address" />
      <div className="location-connector"><span /><button type="button" title="Swap origin and destination" onClick={() => { setOrigin(destination); setDestination(origin) }}><ArrowDown size={14} /></button></div>
      <LocationField label="Destination" value={destination} onChange={setDestination} placeholder="Where are you headed?" />
    </div>
    <div className="form-grid">
      <label className="field"><span><CalendarClock size={15} /> Departure</span><input type="datetime-local" value={departure} onChange={(event) => setDeparture(event.target.value)} required /></label>
      <label className="field"><span><Scale size={15} /> Load weight</span><div className="unit-input"><input type="number" min="0" max="200000" step="100" value={weight} onChange={(event) => setWeight(event.target.value)} required /><em>lb</em></div></label>
    </div>
    <fieldset className="sampling"><legend>Checkpoint interval</legend><div className="sampling-options">{[10, 25, 50].map((miles) => <button type="button" key={miles} aria-pressed={interval === miles} className={interval === miles ? 'active' : ''} onClick={() => setInterval(miles)}>{miles}<small>mi</small></button>)}</div></fieldset>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="primary-button" type="submit" disabled={busy}>{busy ? <><span className="button-spinner" /> Analyzing trip…</> : <>Analyze routes <ArrowRight size={17} /></>}</button>
    <p className="form-footnote"><ArrowUp size={12} /> Weather and route options come from live provider responses.</p>
  </form>
}
