import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MapPin, Search } from 'lucide-react'
import { searchLocations, type Location } from '../lib/api'

type Props = { label: string; value: Location | null; onChange: (location: Location | null) => void; placeholder: string }

export default function LocationField({ label, value, onChange, placeholder }: Props) {
  const [query, setQuery] = useState(value?.name ?? '')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [open, setOpen] = useState(false)
  useEffect(() => { if (value) setQuery(value.name) }, [value])
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 250)
    return () => window.clearTimeout(timer)
  }, [query])
  const normalized = query.trim()
  const { data, isFetching, error } = useQuery({
    queryKey: ['geocode', debouncedQuery], queryFn: ({ signal }) => searchLocations(debouncedQuery, signal),
    enabled: open && debouncedQuery.length >= 2 && debouncedQuery !== value?.name,
    staleTime: 60_000, retry: false,
  })
  const select = (location: Location) => { onChange(location); setQuery(location.name); setOpen(false) }
  return <div className="location-field">
    <label>{label}</label>
    <div className="input-wrap"><MapPin size={17} /><input value={query} placeholder={placeholder} autoComplete="off"
      onFocus={() => setOpen(true)} onBlur={() => window.setTimeout(() => setOpen(false), 140)}
      onChange={(event) => { setQuery(event.target.value); onChange(null); setOpen(true) }} />
      {isFetching && <span className="input-spinner" aria-label="Searching locations" />}
    </div>
    {open && normalized.length >= 2 && (data?.results.length || error) && <div className="suggestions" role="listbox">
      {data?.results.map((location) => <button type="button" role="option" key={`${location.latitude}:${location.longitude}`} onMouseDown={() => select(location)}>
        <Search size={14} /><span><strong>{location.name}</strong><small>{location.address?.region ?? location.address?.country ?? 'Geocoding result'}</small></span>
      </button>)}
      {error && <p className="suggestion-error">{error.message}</p>}
      {data && data.results.length === 0 && <p className="suggestion-error">No matching places found.</p>}
    </div>}
    {query.length > 0 && query.trim().length < 2 && <small className="field-hint">Enter at least 2 characters to search.</small>}
  </div>
}
