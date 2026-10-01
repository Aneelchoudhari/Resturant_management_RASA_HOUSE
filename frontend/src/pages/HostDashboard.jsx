import { useState, useEffect, useCallback } from 'react'
import { fetchTables, fetchReservations, fetchWaitlist, updateTableStatus, staffJoinWaitlist, joinWaitlist, updateReservationStatus, fetchAllocation, fetchAdminCustomers } from '../api'

export default function HostDashboard() {
  const [tables, setTables] = useState([])
  const [reservations, setReservations] = useState([])
  const [waitlist, setWaitlist] = useState([])
  const [allocation, setAllocation] = useState(null)
  const [customers, setCustomers] = useState([])
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [tab, setTab] = useState('floor')  // 'floor' | 'bookings' | 'waitlist'

  // Waitlist form
  const [wlForm, setWlForm] = useState({ guest_name: '', party_size: 2, priority_tier: 1, customer_id: '' })
  const [wlLoading, setWlLoading] = useState(false)

  const load = useCallback(async () => {
    setError('')
    try {
      const [t, r, w, c] = await Promise.all([fetchTables(), fetchReservations(), fetchWaitlist(), fetchAdminCustomers().catch(() => [])])
      setTables(t)
      setReservations(r)
      setWaitlist(w)
      setCustomers(c)
    } catch (e) { setError(String(e)) }
  }, [])

  useEffect(() => { load() }, [load])

  const changeTableStatus = async (tableId, status) => {
    setActionError('')
    try { await updateTableStatus(tableId, status); await load() }
    catch (e) { setActionError(String(e)) }
  }

  const changeReservationStatus = async (id, status) => {
    setActionError('')
    try { await updateReservationStatus(id, { status }); await load() }
    catch (e) { setActionError(String(e)) }
  }

  const addToWaitlist = async (e) => {
    e.preventDefault()
    setWlLoading(true)
    setActionError('')
    try {
      // VIP (1) and Reservation (2) require staff auth; Walk-in (3) is public
      const payload = {
        guest_name: wlForm.guest_name,
        party_size: wlForm.party_size,
        priority_tier: Number(wlForm.priority_tier),
        customer_id: wlForm.customer_id ? Number(wlForm.customer_id) : null,
      }
      if (payload.priority_tier <= 2) {
        await staffJoinWaitlist(payload)
      } else {
        await joinWaitlist(payload)
      }
      setWlForm({ guest_name: '', party_size: 2, priority_tier: 1, customer_id: '' })
      await load()
    }
    catch (err) { setActionError(String(err)) }
    finally { setWlLoading(false) }
  }

  const runAllocation = async () => {
    setActionError('')
    try { setAllocation(await fetchAllocation()) }
    catch (e) { setActionError(String(e)) }
  }

  const todayResv = reservations.filter(r => {
    const today = new Date().toISOString().slice(0, 10)
    return String(r.start_time).slice(0, 10) === today
  })

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ margin: 0 }}>Host / Floor Manager</h1>
          <p style={{ color: '#64748b', margin: '0.25rem 0 0' }}>Tables, reservations, and guest flow</p>
        </div>
        <button className="btn btn-neutral" onClick={load}>↻ Refresh</button>
      </div>

      {error && <p className="error">{error}</p>}
      {actionError && <p className="error">{actionError}</p>}

      {/* Stats */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {[
          { label: 'Available tables', value: tables.filter(t => t.status === 'available').length, color: '#22c55e' },
          { label: 'Occupied', value: tables.filter(t => t.status === 'occupied').length, color: '#ef4444' },
          { label: "Today's bookings", value: todayResv.length, color: '#f59e0b' },
          { label: 'Waiting guests', value: waitlist.length, color: '#8b5cf6' },
        ].map(s => (
          <div key={s.label} style={{ flex: 1, minWidth: 110, background: '#fff', borderRadius: 12, padding: '0.9rem 1.2rem', border: '1px solid #e2e8f0', borderTop: `4px solid ${s.color}` }}>
            <div style={{ fontSize: '1.8rem', fontWeight: 800, color: s.color }}>{s.value}</div>
            <div style={{ color: '#6b7280', fontSize: '0.82rem' }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        {[['floor', '▦ Floor Plan'], ['bookings', '📅 Reservations'], ['waitlist', '◷ Waitlist']].map(([key, label]) => (
          <button key={key} className={`btn ${tab === key ? 'btn-primary' : 'btn-neutral'}`} onClick={() => setTab(key)}>{label}</button>
        ))}
      </div>

      {/* Floor Plan */}
      {tab === 'floor' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <h2 style={{ margin: 0 }}>Floor Plan</h2>
            <button className="btn btn-success" onClick={runAllocation}>Run Allocator</button>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
            <span>🟢 Available</span><span>🔴 Occupied</span><span>🟡 Reserved</span><span>⚪ Cleaning</span>
          </div>
          {tables.length === 0 ? <p className="empty">No tables yet.</p> : (
            <div className="table-grid">
              {tables.map(t => (
                <div key={t.id} className={`table-cell ${({ available: 'table-available', occupied: 'table-occupied', reserved: 'table-reserved' })[t.status] || ''}`}>
                  <div style={{ fontWeight: 700 }}>T{t.number}</div>
                  <div style={{ fontSize: '0.7rem', opacity: 0.8 }}>{t.capacity} seats</div>
                  <div style={{ fontSize: '0.65rem', textTransform: 'capitalize', marginTop: '0.2rem' }}>{t.status}</div>
                  <div style={{ marginTop: '0.4rem', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                    {t.status !== 'available' && (
                      <button className="btn btn-neutral" style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem' }}
                        onClick={() => changeTableStatus(t.id, 'available')}>Free up</button>
                    )}
                    {t.status === 'available' && (
                      <button className="btn btn-neutral" style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem' }}
                        onClick={() => changeTableStatus(t.id, 'reserved')}>Reserve</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
          {allocation && (
            <div style={{ marginTop: '1rem', padding: '0.75rem', background: '#f0fdf4', borderRadius: 8, border: '1px solid #86efac' }}>
              <strong style={{ color: '#166534' }}>Allocation plan:</strong>
              {allocation.assignments?.length === 0 ? <span style={{ color: '#166534', marginLeft: '0.5rem' }}>No pending reservations to assign.</span> : (
                <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.2rem' }}>
                  {allocation.assignments?.map(a => (
                    <li key={a.reservation_id} style={{ fontSize: '0.85rem', color: '#166534' }}>
                      Reservation #{a.reservation_id} → Table #{a.table_number} ({a.party_size} guests)
                    </li>
                  ))}
                </ul>
              )}
              {allocation.unassigned_reservation_ids?.length > 0 && (
                <p style={{ color: '#b91c1c', margin: '0.5rem 0 0', fontSize: '0.85rem' }}>
                  ✗ Unassigned: {allocation.unassigned_reservation_ids.join(', ')}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Reservations */}
      {tab === 'bookings' && (
        <div className="card">
          <h2>Today's Reservations</h2>
          {todayResv.length === 0 ? <p className="empty">No reservations for today.</p> : (
            <table>
              <thead><tr><th>Time</th><th>Guest</th><th>Party</th><th>Status</th><th>Actions</th></tr></thead>
              <tbody>
                {todayResv.map(r => (
                  <tr key={r.id}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{new Date(r.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                    <td><strong>{r.guest_name}</strong></td>
                    <td>{r.party_size} pax</td>
                    <td><span className={`badge ${r.status === 'confirmed' ? 'badge-green' : r.status === 'cancelled' ? 'badge-red' : 'badge-yellow'}`}>{r.status}</span></td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.3rem' }}>
                        {r.status === 'pending' && <button className="btn btn-success" style={{ fontSize: '0.75rem' }} onClick={() => changeReservationStatus(r.id, 'confirmed')}>Confirm</button>}
                        {r.status !== 'cancelled' && <button className="btn btn-neutral" style={{ fontSize: '0.75rem', color: '#ef4444' }} onClick={() => changeReservationStatus(r.id, 'cancelled')}>Cancel</button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {reservations.filter(r => String(r.start_time).slice(0, 10) > new Date().toISOString().slice(0, 10)).length > 0 && (
            <>
              <h3 style={{ marginTop: '1.5rem' }}>Upcoming</h3>
              <table>
                <thead><tr><th>Date & Time</th><th>Guest</th><th>Party</th><th>Status</th></tr></thead>
                <tbody>
                  {reservations.filter(r => String(r.start_time).slice(0, 10) > new Date().toISOString().slice(0, 10)).slice(0, 8).map(r => (
                    <tr key={r.id}>
                      <td style={{ fontSize: '0.85rem' }}>{new Date(r.start_time).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
                      <td>{r.guest_name}</td>
                      <td>{r.party_size} pax</td>
                      <td><span className={`badge ${r.status === 'confirmed' ? 'badge-green' : r.status === 'cancelled' ? 'badge-red' : 'badge-yellow'}`}>{r.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}

      {/* Waitlist */}
      {tab === 'waitlist' && (
        <div>
          <div className="card">
            <h2>Add Guest to Queue</h2>
            <form onSubmit={addToWaitlist}>
              <div className="row">
                <div className="field"><label>Guest Name</label><input value={wlForm.guest_name} onChange={e => setWlForm(f => ({ ...f, guest_name: e.target.value }))} required /></div>
                <div className="field"><label>Party Size</label><input type="number" min="1" max="20" value={wlForm.party_size} onChange={e => setWlForm(f => ({ ...f, party_size: Number(e.target.value) }))} /></div>
                <div className="field">
                  <label>Priority</label>
                  <select value={wlForm.priority_tier} onChange={e => setWlForm(f => ({ ...f, priority_tier: Number(e.target.value) }))}>
                    <option value={1}>⭐ VIP (+20 pts)</option>
                    <option value={2}>📅 Reservation (+10 pts)</option>
                    <option value={3}>🚶 Walk-in</option>
                  </select>
                </div>
                {Number(wlForm.priority_tier) <= 2 && (
                  <div className="field">
                    <label>Customer Account (optional)</label>
                    <select value={wlForm.customer_id} onChange={e => setWlForm(f => ({ ...f, customer_id: e.target.value }))}>
                      <option value="">— No account —</option>
                      {customers.map(c => (
                        <option key={c.id} value={c.id}>{c.name} ({c.email})</option>
                      ))}
                    </select>
                  </div>
                )}
                <button className="btn btn-primary" type="submit" disabled={wlLoading} style={{ alignSelf: 'flex-end' }}>{wlLoading ? 'Adding…' : '+ Add to Queue'}</button>
              </div>
            </form>
          </div>
          <div className="card" style={{ marginTop: '1rem' }}>
            <h2>Current Queue ({waitlist.length})</h2>
            {waitlist.length === 0 ? <p className="empty">Queue is empty.</p> : (
              <table>
                <thead><tr><th>Pos</th><th>Guest</th><th>Party</th><th>Type</th></tr></thead>
                <tbody>
                  {waitlist.map((entry, i) => (
                    <tr key={entry.entry?.id ?? i}>
                      <td>#{i + 1}</td>
                      <td>{entry.entry?.guest_name}</td>
                      <td>{entry.entry?.party_size} pax</td>
                      <td>
                        <span className={`badge ${
                          entry.entry?.priority_tier === 1 ? 'badge-green' :
                          entry.entry?.priority_tier === 2 ? 'badge-blue' : 'badge-gray'
                        }`}>
                          {entry.entry?.priority_tier === 1 ? '⭐ VIP' :
                           entry.entry?.priority_tier === 2 ? '📅 Reservation' : '🚶 Walk-in'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
