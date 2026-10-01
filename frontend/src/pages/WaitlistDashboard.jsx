import { useState, useEffect, useCallback } from 'react'
import { fetchWaitlist, joinWaitlist, staffJoinWaitlist, fetchAdminCustomers } from '../api'
import { getUserRole } from '../auth'

const TIER_INFO = {
  1: { label: '⭐ VIP',         badge: 'badge-green' },
  2: { label: '📅 Reservation', badge: 'badge-blue'  },
  3: { label: '🚶 Walk-in',     badge: 'badge-gray'  },
}

// Roles that can add VIP / Reservation entries
const VIP_ROLES = ['manager', 'receptionist', 'admin']

export default function WaitlistDashboard({ readOnly = false }) {
  const role = getUserRole()
  const canAddVip = !readOnly && VIP_ROLES.includes(role)

  const [queue, setQueue] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Walk-in form (public)
  const [walkInForm, setWalkInForm] = useState({ guest_name: '', party_size: 2 })
  const [walkInMsg, setWalkInMsg] = useState('')

  // Staff VIP/Reservation form
  const [staffForm, setStaffForm] = useState({ guest_name: '', party_size: 2, priority_tier: 1, customer_id: '' })
  const [staffMsg, setStaffMsg] = useState('')
  const [staffLoading, setStaffLoading] = useState(false)
  const [customers, setCustomers] = useState([])

  const load = useCallback(async () => {
    try {
      const data = await fetchWaitlist()
      setQueue(data)
    } catch (e) {
      setError(String(e))
    }
  }, [])

  useEffect(() => {
    load()
    if (canAddVip) {
      fetchAdminCustomers().then(setCustomers).catch(() => setCustomers([]))
    }
  }, [load, canAddVip])

  // Walk-in submit (public endpoint, tier 3 only)
  const submitWalkIn = async (e) => {
    e.preventDefault()
    setLoading(true)
    setWalkInMsg('')
    setError('')
    try {
      await joinWaitlist({ ...walkInForm, priority_tier: 3 })
      setWalkInMsg('Added to queue as Walk-in.')
      setWalkInForm({ guest_name: '', party_size: 2 })
      await load()
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  // VIP/Reservation submit (staff-auth endpoint)
  const submitStaff = async (e) => {
    e.preventDefault()
    setStaffLoading(true)
    setStaffMsg('')
    setError('')
    try {
      const payload = {
        guest_name: staffForm.guest_name,
        party_size: Number(staffForm.party_size),
        priority_tier: Number(staffForm.priority_tier),
        customer_id: staffForm.customer_id ? Number(staffForm.customer_id) : null,
      }
      const result = await staffJoinWaitlist(payload)
      const label = TIER_INFO[payload.priority_tier]?.label || 'Guest'
      setStaffMsg(
        `${payload.guest_name} added as ${label} at position #${result.position}.` +
        (payload.customer_id ? ' Loyalty points awarded.' : '')
      )
      setStaffForm({ guest_name: '', party_size: 2, priority_tier: 1, customer_id: '' })
      await load()
    } catch (err) {
      setError(String(err))
    } finally {
      setStaffLoading(false)
    }
  }

  return (
    <div className="page">
      <h1>Waitlist</h1>

      {/* ── Staff: Add VIP / Reservation ──────────────────────────────────── */}
      {canAddVip && (
        <div className="card" style={{ borderLeft: '4px solid #d8a449' }}>
          <h2>Add VIP or Reservation Customer</h2>
          <p style={{ color: '#475569', marginBottom: '1rem', fontSize: '0.9rem' }}>
            For customers who call ahead. Loyalty points are awarded automatically
            (+20 VIP, +10 Reservation) when a customer account is linked.
          </p>
          <form onSubmit={submitStaff}>
            <div className="row">
              <div className="field">
                <label>Guest Name</label>
                <input
                  value={staffForm.guest_name}
                  onChange={e => setStaffForm(f => ({ ...f, guest_name: e.target.value }))}
                  required
                  placeholder="Guest name"
                />
              </div>
              <div className="field">
                <label>Party Size</label>
                <input
                  type="number" min="1" max="20"
                  value={staffForm.party_size}
                  onChange={e => setStaffForm(f => ({ ...f, party_size: Number(e.target.value) }))}
                />
              </div>
              <div className="field">
                <label>Priority</label>
                <select
                  value={staffForm.priority_tier}
                  onChange={e => setStaffForm(f => ({ ...f, priority_tier: Number(e.target.value) }))}
                >
                  <option value={1}>⭐ VIP (+20 pts)</option>
                  <option value={2}>📅 Reservation (+10 pts)</option>
                </select>
              </div>
              <div className="field">
                <label>Link Customer Account (optional)</label>
                <select
                  value={staffForm.customer_id}
                  onChange={e => setStaffForm(f => ({ ...f, customer_id: e.target.value }))}
                >
                  <option value="">— Walk-in / no account —</option>
                  {customers.map(c => (
                    <option key={c.id} value={c.id}>{c.name} ({c.email})</option>
                  ))}
                </select>
              </div>
            </div>
            {staffMsg && <p className="success" style={{ color: '#276749', margin: 0 }}>{staffMsg}</p>}
            <button className="btn btn-primary" type="submit" disabled={staffLoading}>
              {staffLoading ? 'Adding…' : '+ Add to Queue'}
            </button>
          </form>
        </div>
      )}

      {/* ── Walk-in form (public, non-readOnly) ───────────────────────────── */}
      {!readOnly && (
        <div className="card">
          <h2>Add Walk-in Guest</h2>
          <p style={{ color: '#475569', marginBottom: '1rem', fontSize: '0.9rem' }}>
            Walk-in guests join at standard priority.
          </p>
          <form onSubmit={submitWalkIn}>
            <div className="row">
              <div className="field">
                <label>Guest Name</label>
                <input value={walkInForm.guest_name} onChange={e => setWalkInForm(f => ({ ...f, guest_name: e.target.value }))} required />
              </div>
              <div className="field">
                <label>Party Size</label>
                <input type="number" min="1" max="20" value={walkInForm.party_size} onChange={e => setWalkInForm(f => ({ ...f, party_size: Number(e.target.value) }))} />
              </div>
              <button className="btn btn-neutral" type="submit" disabled={loading} style={{ alignSelf: 'flex-end' }}>
                {loading ? 'Adding…' : '🚶 Add Walk-in'}
              </button>
            </div>
            {walkInMsg && <p style={{ color: '#276749', margin: 0 }}>{walkInMsg}</p>}
          </form>
        </div>
      )}

      {error && <p className="error">{error}</p>}

      {/* ── Priority legend ────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
        {Object.entries(TIER_INFO).map(([tier, info]) => (
          <span key={tier} className={`badge ${info.badge}`} style={{ fontSize: '0.8rem' }}>
            {info.label}
          </span>
        ))}
        <span style={{ color: '#64748b', fontSize: '0.8rem' }}>
          Priority order: VIP → Reservation → Walk-in
        </span>
      </div>

      {/* ── Queue ─────────────────────────────────────────────────────────── */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <h2 style={{ margin: 0 }}>Current Queue ({queue.length})</h2>
          <button className="btn btn-neutral" onClick={load}>↻ Refresh</button>
        </div>
        {queue.length === 0 ? (
          <p className="empty">Queue is empty</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Pos</th>
                <th>Guest</th>
                <th>Party</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {queue.map((entry, i) => {
                const tier = entry.entry?.priority_tier ?? 3
                const info = TIER_INFO[tier] || TIER_INFO[3]
                return (
                  <tr key={entry.entry?.id ?? i}>
                    <td><strong>#{i + 1}</strong></td>
                    <td>{entry.entry?.guest_name}</td>
                    <td>{entry.entry?.party_size} pax</td>
                    <td><span className={`badge ${info.badge}`}>{info.label}</span></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
