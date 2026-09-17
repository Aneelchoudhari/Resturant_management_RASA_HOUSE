import { useState } from 'react'
import { createReservation, joinWaitlist } from '../api'

export default function ReservationForm() {
  const [form, setForm] = useState({
    guest_name: '',
    party_size: 2,
    start_time: '',
    duration_minutes: 60,
    priority_tier: 2,
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k) => (e) =>
    setForm((f) => ({
      ...f,
      [k]: ['party_size', 'duration_minutes', 'priority_tier'].includes(k)
        ? Number(e.target.value)
        : e.target.value,
    }))

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setResult(null)
    setLoading(true)
    try {
      // 1. Create reservation (feeds into interval scheduler)
      const reservation = await createReservation({
        guest_name: form.guest_name,
        party_size: form.party_size,
        start_time: new Date(form.start_time).toISOString(),
        duration_minutes: form.duration_minutes,
      })
      // 2. Also add to waitlist (priority queue)
      const waitlistEntry = await joinWaitlist({
        guest_name: form.guest_name,
        party_size: form.party_size,
        priority_tier: form.priority_tier,
      })
      setResult({ reservation, waitlistEntry })
      setForm({ guest_name: '', party_size: 2, start_time: '', duration_minutes: 60, priority_tier: 2 })
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page" style={{ maxWidth: 600 }}>
      <h1>New Reservation</h1>
      <div className="card">
        <p style={{ fontSize: '0.85rem', color: '#718096', marginBottom: '1rem' }}>
          Creates a pending reservation (for the interval scheduler) and adds the guest to the
          priority waitlist queue.
        </p>
        <form onSubmit={submit}>
          <div className="field">
            <label>Guest Name</label>
            <input value={form.guest_name} onChange={set('guest_name')} required />
          </div>
          <div className="row">
            <div className="field">
              <label>Party Size</label>
              <input type="number" min="1" max="20" value={form.party_size} onChange={set('party_size')} />
            </div>
            <div className="field">
              <label>Priority Tier</label>
              <select value={form.priority_tier} onChange={set('priority_tier')}>
                <option value={1}>1 — VIP</option>
                <option value={2}>2 — Reservation</option>
                <option value={3}>3 — Walk-in</option>
              </select>
            </div>
          </div>
          <div className="row">
            <div className="field">
              <label>Start Date & Time</label>
              <input type="datetime-local" value={form.start_time} onChange={set('start_time')} required />
            </div>
            <div className="field">
              <label>Duration (minutes)</label>
              <input type="number" min="15" step="15" value={form.duration_minutes} onChange={set('duration_minutes')} />
            </div>
          </div>
          {error && <p className="error">{error}</p>}
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? 'Submitting…' : 'Create Reservation'}
          </button>
        </form>
      </div>

      {result && (
        <div className="card" style={{ borderLeft: '4px solid #48bb78' }}>
          <h2 style={{ color: '#276749' }}>✓ Reservation Created</h2>
          <p className="mt1"><strong>Reservation ID:</strong> #{result.reservation.id}</p>
          <p><strong>Guest:</strong> {result.reservation.guest_name}</p>
          <p><strong>Party:</strong> {result.reservation.party_size} pax</p>
          <p><strong>Status:</strong>{' '}
            <span className="badge badge-yellow">{result.reservation.status}</span>
          </p>
          <p className="mt1"><strong>Waitlist position added</strong> — priority score:{' '}
            <span style={{ fontFamily: 'monospace' }}>{result.waitlistEntry.priority_score?.toFixed(0)}</span>
          </p>
          <p style={{ fontSize: '0.8rem', color: '#718096', marginTop: '0.5rem' }}>
            Run the Table Allocator on the Tables page to assign a table.
          </p>
        </div>
      )}
    </div>
  )
}
