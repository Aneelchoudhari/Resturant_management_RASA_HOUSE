import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchAdminAudit, fetchStaffCustomers, fetchAdminReports,
  fetchMenuItems, fetchOrders, fetchReservations, fetchStaff,
  fetchTables, fetchWaitlist, adminCreateTable, adminAllocateTable, staffJoinWaitlist,
} from '../api'

const today = new Date().toISOString().slice(0, 10)

const metricGroups = [
  { label: "Today's bookings", key: 'todayBookings', tone: 'gold', link: '/reservation' },
  { label: 'Upcoming bookings', key: 'upcomingBookings', tone: 'blue', link: '/reservation' },
  { label: 'Available tables', key: 'availableTables', tone: 'green', link: '/tables' },
  { label: 'Occupied tables', key: 'occupiedTables', tone: 'red', link: '/tables' },
  { label: "Today's customers", key: 'todayCustomers', tone: 'violet', link: '/history' },
  { label: "Today's revenue", key: 'todayRevenue', tone: 'gold', link: '/history' },
  { label: 'Pending orders', key: 'pendingOrders', tone: 'orange', link: '/history' },
  { label: 'Completed orders', key: 'completedOrders', tone: 'green', link: '/history' },
]

const prettyStatus = (value) => String(value || '').replace('_', ' ')

const TIER_LABEL = { 1: 'VIP', 2: 'Reservation', 3: 'Walk-in' }
const TIER_BADGE = { 1: 'badge-green', 2: 'badge-blue', 3: 'badge-gray' }

export default function AdminDashboard() {
  const [data, setData] = useState({ reservations: [], orders: [], menu: [], tables: [], staff: [], waitlist: [], customers: [], audit: [], reports: [] })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  // Table creation form
  const [tableForm, setTableForm] = useState({ number: '', capacity: '' })
  const [tableMsg, setTableMsg] = useState('')
  const [tableErr, setTableErr] = useState('')

  // Master allocation form
  const [allocForm, setAllocForm] = useState({ table_id: '', customer_id: '', guest_name: '' })
  const [allocMsg, setAllocMsg] = useState('')
  const [allocErr, setAllocErr] = useState('')

  // Waitlist add form (VIP / Reservation)
  const [wlForm, setWlForm] = useState({ guest_name: '', party_size: 2, priority_tier: 1, customer_id: '' })
  const [wlMsg, setWlMsg] = useState('')
  const [wlErr, setWlErr] = useState('')
  const [wlLoading, setWlLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [reservations, orders, menu, tables, staff, waitlist, customers, audit, reports] = await Promise.all([
        fetchReservations(), fetchOrders(), fetchMenuItems(), fetchTables(), fetchStaff(), fetchWaitlist(), fetchStaffCustomers(), fetchAdminAudit(), fetchAdminReports(),
      ])
      setData({ reservations, orders, menu, tables, staff, waitlist, customers, audit, reports })
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const stats = useMemo(() => {
    const todayReservations = data.reservations.filter((item) => String(item.start_time).slice(0, 10) === today)
    const todayOrders = data.orders.filter((item) => String(item.created_at).slice(0, 10) === today)
    const upcomingBookings = data.reservations.filter((item) => String(item.start_time).slice(0, 10) >= today && item.status !== 'cancelled')
    return {
      todayBookings: todayReservations.length,
      upcomingBookings: upcomingBookings.length,
      availableTables: data.tables.filter((item) => item.status === 'available').length,
      occupiedTables: data.tables.filter((item) => item.status === 'occupied').length,
      todayCustomers: new Set(todayReservations.map((item) => item.guest_name)).size,
      todayRevenue: todayOrders.reduce((total, item) => total + Number(item.total_amount || 0), 0),
      pendingOrders: data.orders.filter((item) => ['placed', 'accepted', 'preparing', 'ready', 'in_progress'].includes(item.status)).length,
      completedOrders: data.orders.filter((item) => item.status === 'completed').length,
      cancelledOrders: data.orders.filter((item) => item.status === 'cancelled').length,
      availableMenu: data.menu.filter((item) => item.available).length,
      unavailableMenu: data.menu.filter((item) => !item.available).length,
    }
  }, [data])

  // ── Table creation ──────────────────────────────────────────────────────────
  const handleCreateTable = async (e) => {
    e.preventDefault()
    setTableErr('')
    setTableMsg('')
    try {
      await adminCreateTable({ number: Number(tableForm.number), capacity: Number(tableForm.capacity) })
      setTableMsg(`Table #${tableForm.number} (${tableForm.capacity} seats) created and now available.`)
      setTableForm({ number: '', capacity: '' })
      await load()
    } catch (err) { setTableErr(String(err)) }
  }

  // ── Master allocation ───────────────────────────────────────────────────────
  const handleAllocate = async (e) => {
    e.preventDefault()
    setAllocErr('')
    setAllocMsg('')
    try {
      const payload = {
        table_id: Number(allocForm.table_id),
        customer_id: allocForm.customer_id ? Number(allocForm.customer_id) : null,
        guest_name: allocForm.guest_name || null,
        party_size: Number(allocForm.party_size || 1),
      }
      const result = await adminAllocateTable(payload)
      setAllocMsg(`Table #${result.table_number} allocated to ${result.guest_name}. Status: ${result.status}.`)
      setAllocForm({ table_id: '', customer_id: '', guest_name: '' })
      await load()
    } catch (err) { setAllocErr(String(err)) }
  }

  // ── Waitlist add (VIP / Reservation) ───────────────────────────────────────
  const handleWaitlistAdd = async (e) => {
    e.preventDefault()
    setWlLoading(true)
    setWlErr('')
    setWlMsg('')
    try {
      const payload = {
        guest_name: wlForm.guest_name,
        party_size: Number(wlForm.party_size),
        priority_tier: Number(wlForm.priority_tier),
        customer_id: wlForm.customer_id ? Number(wlForm.customer_id) : null,
      }
      const result = await staffJoinWaitlist(payload)
      const tierLabel = TIER_LABEL[payload.priority_tier] || 'Unknown'
      setWlMsg(`${payload.guest_name} added to waitlist as ${tierLabel} at position #${result.position}.${payload.customer_id ? ' Loyalty points awarded.' : ''}`)
      setWlForm({ guest_name: '', party_size: 2, priority_tier: 1, customer_id: '' })
      await load()
    } catch (err) { setWlErr(String(err)) }
    finally { setWlLoading(false) }
  }

  const availableTables = data.tables.filter((t) => t.status === 'available')

  return (
    <main className="admin-page">
      <header className="admin-header">
        <div><p className="admin-kicker">Restaurant control room</p><h1>Good morning, Admin</h1><p className="admin-subtitle">Here is what is happening across the restaurant today.</p></div>
        <div className="admin-header-actions"><span className="live-indicator"><i /> Live data</span><button className="btn btn-neutral" onClick={load} disabled={loading}>{loading ? 'Refreshing...' : '↻ Refresh'}</button></div>
      </header>
      {error && <p className="error">Could not load the complete dashboard: {error}</p>}
      <section className="admin-status-strip"><span className="status-pulse" /> <strong>Restaurant is open</strong><span>•</span><span>{data.waitlist.length} guests currently waiting</span><span>•</span><span>{data.staff.length} staff accounts provisioned</span></section>
      <section className="metric-grid">{metricGroups.map((metric) => <Link to={metric.link} className={`metric-card metric-${metric.tone}`} key={metric.key}><span>{metric.label}</span><strong>{metric.key === 'todayRevenue' ? `₹${stats[metric.key].toLocaleString()}` : stats[metric.key]}</strong><small>View details ↗</small></Link>)}</section>

      {/* ── Admin Controls Row ────────────────────────────────────────────── */}
      <section className="admin-columns" style={{ marginTop: '1.5rem' }}>

        {/* Add Table */}
        <div className="admin-panel">
          <div className="panel-heading">
            <div><p className="admin-kicker">Table Management</p><h2>Add New Table</h2></div>
          </div>
          <p style={{ color: '#64748b', fontSize: '0.85rem', marginBottom: '1rem' }}>
            New tables become immediately available on the floor plan.
          </p>
          <form onSubmit={handleCreateTable}>
            <div className="row">
              <div className="field">
                <label>Table Number</label>
                <input
                  type="number" min="1"
                  value={tableForm.number}
                  onChange={(e) => setTableForm({ ...tableForm, number: e.target.value })}
                  placeholder="e.g. 12"
                  required
                />
              </div>
              <div className="field">
                <label>Capacity (seats)</label>
                <input
                  type="number" min="1" max="50"
                  value={tableForm.capacity}
                  onChange={(e) => setTableForm({ ...tableForm, capacity: e.target.value })}
                  placeholder="e.g. 4"
                  required
                />
              </div>
            </div>
            {tableMsg && <p className="success" style={{ marginBottom: '0.5rem' }}>{tableMsg}</p>}
            {tableErr && <p className="error" style={{ marginBottom: '0.5rem' }}>{tableErr}</p>}
            <button className="btn btn-primary" type="submit">+ Create Table</button>
          </form>

          {/* Existing tables quick list */}
          {data.tables.length > 0 && (
            <div style={{ marginTop: '1rem' }}>
              <p style={{ fontWeight: 600, fontSize: '0.85rem', color: '#475569', marginBottom: '0.5rem' }}>
                Current tables ({data.tables.length})
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                {data.tables.map((t) => (
                  <span
                    key={t.id}
                    style={{
                      fontSize: '0.75rem', padding: '0.2rem 0.6rem', borderRadius: 6,
                      background: t.status === 'available' ? '#dcfce7' : t.status === 'occupied' ? '#fee2e2' : '#fef3c7',
                      color: '#1e293b', border: '1px solid #e2e8f0',
                    }}
                  >
                    T{t.number} ({t.capacity}p)
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Master Table Allocation */}
        <div className="admin-panel">
          <div className="panel-heading">
            <div><p className="admin-kicker">Master Control</p><h2>Allocate Table</h2></div>
          </div>
          <p style={{ color: '#64748b', fontSize: '0.85rem', marginBottom: '1rem' }}>
            Admin can seat a customer at an available table. Existing reservations are protected.
          </p>
          <form onSubmit={handleAllocate}>
            <div className="row">
              <div className="field">
                <label>Table</label>
                <select
                  value={allocForm.table_id}
                  onChange={(e) => setAllocForm({ ...allocForm, table_id: e.target.value })}
                  required
                >
                  <option value="">— Select table —</option>
                  {availableTables.map((t) => (
                    <option key={t.id} value={t.id}>
                      T{t.number} ({t.capacity} seats) — {t.status}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="field">
              <label>Party Size</label>
              <input
                type="number" min="1" max="100"
                value={allocForm.party_size || 1}
                onChange={(e) => setAllocForm({ ...allocForm, party_size: e.target.value })}
                required
              />
            </div>
            <div className="row">
              <div className="field">
                <label>Customer Account (optional)</label>
                <select
                  value={allocForm.customer_id}
                  onChange={(e) => setAllocForm({ ...allocForm, customer_id: e.target.value, guest_name: '' })}
                >
                  <option value="">— Walk-in guest —</option>
                  {data.customers.map((c) => (
                    <option key={c.id} value={c.id}>{c.name} ({c.email})</option>
                  ))}
                </select>
              </div>
              {!allocForm.customer_id && (
                <div className="field">
                  <label>Guest Name</label>
                  <input
                    value={allocForm.guest_name}
                    onChange={(e) => setAllocForm({ ...allocForm, guest_name: e.target.value })}
                    placeholder="Guest name"
                    required={!allocForm.customer_id}
                  />
                </div>
              )}
            </div>
            {allocMsg && <p className="success" style={{ marginBottom: '0.5rem' }}>{allocMsg}</p>}
            {allocErr && <p className="error" style={{ marginBottom: '0.5rem' }}>{allocErr}</p>}
            <button className="btn btn-primary" type="submit">Allocate Table</button>
          </form>
        </div>
      </section>

      {/* ── Add to Waitlist (VIP / Reservation) ─────────────────────────── */}
      <section className="admin-columns" style={{ marginTop: '1.5rem' }}>
        <div className="admin-panel" style={{ gridColumn: '1 / -1' }}>
          <div className="panel-heading">
            <div><p className="admin-kicker">Queue Management</p><h2>Add Customer to Waitlist</h2></div>
            <Link to="/waitlist">View full queue ↗</Link>
          </div>
          <p style={{ color: '#64748b', fontSize: '0.85rem', marginBottom: '1rem' }}>
            Admin can add VIP and Reservation customers. Loyalty points are awarded automatically (+20 VIP, +10 Reservation) when a customer account is linked.
          </p>
          <form onSubmit={handleWaitlistAdd}>
            <div className="row">
              <div className="field">
                <label>Guest Name</label>
                <input
                  value={wlForm.guest_name}
                  onChange={(e) => setWlForm({ ...wlForm, guest_name: e.target.value })}
                  required
                  placeholder="Customer name"
                />
              </div>
              <div className="field">
                <label>Party Size</label>
                <input
                  type="number" min="1" max="20"
                  value={wlForm.party_size}
                  onChange={(e) => setWlForm({ ...wlForm, party_size: Number(e.target.value) })}
                />
              </div>
              <div className="field">
                <label>Priority</label>
                <select
                  value={wlForm.priority_tier}
                  onChange={(e) => setWlForm({ ...wlForm, priority_tier: Number(e.target.value) })}
                >
                  <option value={1}>⭐ VIP (+20 pts)</option>
                  <option value={2}>📅 Reservation (+10 pts)</option>
                </select>
              </div>
              <div className="field">
                <label>Customer Account (optional)</label>
                <select
                  value={wlForm.customer_id}
                  onChange={(e) => setWlForm({ ...wlForm, customer_id: e.target.value })}
                >
                  <option value="">— No account / Walk-in —</option>
                  {data.customers.map((c) => (
                    <option key={c.id} value={c.id}>{c.name} ({c.email})</option>
                  ))}
                </select>
              </div>
            </div>
            {wlMsg && <p className="success" style={{ marginBottom: '0.5rem' }}>{wlMsg}</p>}
            {wlErr && <p className="error" style={{ marginBottom: '0.5rem' }}>{wlErr}</p>}
            <button className="btn btn-primary" type="submit" disabled={wlLoading}>
              {wlLoading ? 'Adding…' : '+ Add to Queue'}
            </button>
          </form>

          {/* Waitlist preview */}
          {data.waitlist.length > 0 && (
            <div style={{ marginTop: '1.25rem' }}>
              <p style={{ fontWeight: 600, fontSize: '0.85rem', color: '#475569', marginBottom: '0.5rem' }}>
                Current Queue ({data.waitlist.length}) — Priority order: VIP → Reservation → Walk-in
              </p>
              <table>
                <thead>
                  <tr><th>#</th><th>Guest</th><th>Party</th><th>Type</th></tr>
                </thead>
                <tbody>
                  {data.waitlist.slice(0, 8).map((item, i) => (
                    <tr key={item.entry?.id ?? i}>
                      <td>#{i + 1}</td>
                      <td><strong>{item.entry?.guest_name}</strong></td>
                      <td>{item.entry?.party_size} pax</td>
                      <td>
                        <span className={`badge ${TIER_BADGE[item.entry?.priority_tier] || 'badge-gray'}`}>
                          {TIER_LABEL[item.entry?.priority_tier] || `Tier ${item.entry?.priority_tier}`}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {/* ── Existing panels ───────────────────────────────────────────────── */}
      <section className="admin-columns admin-columns-bottom">
        <div className="admin-panel"><div className="panel-heading"><div><p className="admin-kicker">Service pulse</p><h2>Orders at a glance</h2></div><Link to="/history">View all ↗</Link></div><div className="order-bars"><div><span>New &amp; preparing</span><b>{stats.pendingOrders}</b><i><em style={{ width: `${Math.min(100, stats.pendingOrders * 12)}%` }} /></i></div><div><span>Completed</span><b>{stats.completedOrders}</b><i><em className="bar-green" style={{ width: `${Math.min(100, stats.completedOrders * 12)}%` }} /></i></div><div><span>Cancelled</span><b>{stats.cancelledOrders}</b><i><em className="bar-red" style={{ width: `${Math.min(100, stats.cancelledOrders * 12)}%` }} /></i></div></div></div>
        <div className="admin-panel"><div className="panel-heading"><div><p className="admin-kicker">Attention</p><h2>Menu availability</h2></div><Link to="/menu">Manage menu ↗</Link></div><div className="availability-row"><strong>{stats.availableMenu}</strong><span>available items</span><strong className="unavailable-number">{stats.unavailableMenu}</strong><span>unavailable</span></div><p className="panel-note">Low-stock tracking will appear here as inventory quantities are added to menu items.</p></div>
      </section>
      <section className="admin-columns admin-columns-bottom">
        <div className="admin-panel"><div className="panel-heading"><div><p className="admin-kicker">Next on the floor</p><h2>Upcoming bookings</h2></div><Link to="/reservation">Manage ↗</Link></div>{data.reservations.filter((item) => String(item.start_time).slice(0, 10) >= today).slice(0, 5).map((item) => <div className="booking-row" key={item.id}><span className="booking-time">{new Date(item.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span><div><strong>{item.guest_name}</strong><small>{item.party_size} guests · Table {item.table_id || 'unassigned'}</small></div><span className={`badge badge-${item.status === 'confirmed' ? 'green' : item.status === 'cancelled' ? 'red' : 'yellow'}`}>{prettyStatus(item.status)}</span></div>)}{!data.reservations.length && <p className="empty">No bookings recorded yet.</p>}</div>
        <div className="admin-panel quick-actions"><div className="panel-heading"><div><p className="admin-kicker">Command shortcuts</p><h2>Run the restaurant</h2></div></div><Link to="/staff/manage">＋ Create staff account <span>Admin only</span></Link><Link to="/tables">▦ Open floor plan <span>Tables &amp; allocation</span></Link><Link to="/kitchen">◉ Open kitchen queue <span>Preparation status</span></Link><Link to="/waitlist">◷ Review waitlist <span>{data.waitlist.length} waiting</span></Link></div>
      </section>
      <section className="admin-columns admin-columns-bottom">
        <div className="admin-panel"><div className="panel-heading"><div><p className="admin-kicker">Seven-day trend</p><h2>Bookings &amp; revenue</h2></div><span className="panel-note">Reports</span></div><div className="report-list">{data.reports.map((item) => <div className="report-row" key={item.date}><span>{new Date(`${item.date}T12:00:00`).toLocaleDateString([], { weekday: 'short' })}</span><i><em style={{ width: `${Math.min(100, item.bookings * 18)}%` }} /></i><b>{item.bookings} bookings</b><strong>₹{Number(item.revenue || 0).toLocaleString()}</strong></div>)}</div></div>
        <div className="admin-panel"><div className="panel-heading"><div><p className="admin-kicker">People &amp; accountability</p><h2>Recent activity</h2></div><span className="panel-note">{data.customers.length} customers</span></div>{data.audit.slice(0, 5).map((item) => <div className="activity-row" key={item.id}><span className="activity-dot" /><div><strong>{item.action}</strong><small>{item.staff_name} · {item.role} · {new Date(item.created_at).toLocaleString()}</small></div></div>)}{!data.audit.length && <p className="empty">Activity will appear as admin actions are performed.</p>}</div>
      </section>
    </main>
  )
}