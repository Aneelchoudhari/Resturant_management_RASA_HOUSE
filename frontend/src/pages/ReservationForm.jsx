import { useRef, useState } from 'react'
import { createReservation } from '../api'
import { isStaffUser, getUserRole } from '../auth'

const VIP_ROLES = ['manager', 'receptionist', 'admin']

export default function ReservationForm() {
  const staffMode = isStaffUser()
  const role = getUserRole()
  const canSetPriority = VIP_ROLES.includes(role)

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
  const idempotencyKey = useRef(null)

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
      idempotencyKey.current ||= crypto.randomUUID()
      const reservation = await createReservation({
        guest_name: form.guest_name,
        party_size: form.party_size,
        start_time: new Date(form.start_time).toISOString(),
        duration_minutes: form.duration_minutes,
        waitlist_priority_tier: staffMode && canSetPriority ? form.priority_tier : 3,
      }, idempotencyKey.current)
      setResult({ reservation })
      idempotencyKey.current = null
      setForm({ guest_name: '', party_size: 2, start_time: '', duration_minutes: 60, priority_tier: 2 })
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page" style={{ maxWidth: 600 }}>
      <h1>{staffMode ? 'New Reservation' : 'Reserve a Table'}</h1>
      <div className="card">
        {!staffMode && (
          <p style={{ fontSize: '0.85rem', color: '#718096', marginBottom: '1rem' }}>
            Book your table at RASA HOUSE. We will confirm your reservation shortly.
          </p>
        )}
        {staffMode && (
          <p style={{ fontSize: '0.85rem', color: '#718096', marginBottom: '1rem' }}>
            Creates a pending reservation and adds the guest to the priority waitlist queue.
          </p>
        )}
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
            {/* Priority tier selector only visible to manager/receptionist/admin */}
            {canSetPriority && (
              <div className="field">
                <label>Priority</label>
                <select value={form.priority_tier} onChange={set('priority_tier')}>
                  <option value={1}>⭐ VIP</option>
                  <option value={2}>📅 Reservation</option>
                </select>
              </div>
            )}
          </div>
          <div className="row">
            <div className="field">
              <label>Date &amp; Time</label>
              <input type="datetime-local" value={form.start_time} onChange={set('start_time')} required />
            </div>
            <div className="field">
              <label>Duration (minutes)</label>
              <input type="number" min="15" step="15" value={form.duration_minutes} onChange={set('duration_minutes')} />
            </div>
          </div>
          {error && <p className="error">{error}</p>}
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? 'Submitting…' : staffMode ? 'Create Reservation' : 'Reserve Table'}
          </button>
        </form>
      </div>

      {result && (
        <div className="card" style={{ borderLeft: '4px solid #48bb78' }}>
          <h2 style={{ color: '#276749' }}>✓ Reservation {result.reservation.status === 'confirmed' ? 'Confirmed' : 'Created'}</h2>
          <p className="mt1"><strong>Reservation ID:</strong> #{result.reservation.id}</p>
          <p><strong>Guest:</strong> {result.reservation.guest_name}</p>
          <p><strong>Party:</strong> {result.reservation.party_size} guests</p>
          <p><strong>Status:</strong>{' '}
            <span className="badge badge-yellow">{result.reservation.status}</span>
          </p>
          {staffMode && (
            <p className="mt1" style={{ fontSize: '0.8rem', color: '#718096' }}>
              Added to the waitlist with this reservation. Run the allocator preview on the Tables page and save its assignments.
            </p>
          )}
          {!staffMode && (
            <p className="mt1" style={{ fontSize: '0.85rem', color: '#475569' }}>
              Our team will confirm your table assignment. Check <strong>My Account</strong> for updates.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
