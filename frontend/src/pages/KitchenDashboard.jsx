import { useState, useEffect, useCallback } from 'react'
import { fetchKitchenQueue, fetchActiveOrders, updateOrderStatus, claimKitchenTicket, startKitchenTicket, completeKitchenTicket, releaseKitchenTicket } from '../api'
import { getUserRole } from '../auth'

const STATIONS = ['grill', 'dessert', 'drinks', 'sides']

const stationColor = (station) => ({
  grill: '#dc2626',
  dessert: '#d97706',
  drinks: '#2563eb',
  sides: '#059669',
})[station] || '#6b7280'

const timeSince = (createdAt) => {
  const mins = Math.floor((Date.now() - new Date(createdAt)) / 60000)
  if (mins < 1) return 'just now'
  if (mins === 1) return '1 min ago'
  return `${mins} min ago`
}

const isChef = () => ['chef', 'admin', 'manager'].includes(getUserRole())

export default function KitchenDashboard() {
  const [station, setStation] = useState('grill')
  const [queue, setQueue] = useState(null)
  const [activeOrders, setActiveOrders] = useState([])
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [tab, setTab] = useState('orders')  // 'queue' | 'orders'

  const load = useCallback(async () => {
    setError('')
    try {
      const [q, orders] = await Promise.all([
        fetchKitchenQueue(station),
        fetchActiveOrders(),
      ])
      setQueue(q)
      setActiveOrders(orders.filter(o => ['placed', 'accepted', 'preparing', 'ready'].includes(o.status)))
    } catch (e) {
      setError(String(e))
    }
  }, [station])

  useEffect(() => { load() }, [load])

  // Auto-refresh every 20 seconds
  useEffect(() => {
    const interval = setInterval(load, 20000)
    return () => clearInterval(interval)
  }, [load])

  const changeStatus = async (orderId, status) => {
    setActionError('')
    try {
      await updateOrderStatus(orderId, status)
      await load()
    } catch (e) {
      setActionError(String(e))
    }
  }

  const changeTicket = async (ticket, action) => {
    setActionError('')
    try {
      if (action === 'claim') await claimKitchenTicket(ticket.ticket_id)
      if (action === 'start') await startKitchenTicket(ticket.ticket_id)
      if (action === 'complete') await completeKitchenTicket(ticket.ticket_id)
      if (action === 'release') await releaseKitchenTicket(ticket.ticket_id)
      await load()
    } catch (e) {
      setActionError(String(e))
    }
  }

  const kitchenOrders = activeOrders
  const placedCount = activeOrders.filter(o => o.status === 'placed').length
  const preparingCount = activeOrders.filter(o => o.status === 'preparing' || o.status === 'accepted').length
  const readyCount = activeOrders.filter(o => o.status === 'ready').length

  const roleLabel = isChef() ? 'Chef Dashboard' : 'Kitchen Display'
  const roleDesc = isChef()
    ? 'Manage all kitchen orders, prioritise and coordinate preparation'
    : 'Accept and prepare orders — update status as you cook'

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ margin: 0 }}>{roleLabel}</h1>
          <p style={{ color: '#64748b', margin: '0.25rem 0 0' }}>{roleDesc}</p>
        </div>
        <button className="btn btn-neutral" onClick={load}>↻ Refresh</button>
      </div>

      {error && <p className="error">{error}</p>}
      {actionError && <p className="error">{actionError}</p>}

      {/* Stats strip */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {[
          { label: 'New orders', value: placedCount, color: '#f59e0b' },
          { label: 'Accepted / Cooking', value: preparingCount, color: '#3b82f6' },
          { label: 'Ready to serve', value: readyCount, color: '#22c55e' },
        ].map(s => (
          <div key={s.label} style={{ flex: 1, minWidth: 120, background: '#fff', borderRadius: 12, padding: '0.9rem 1.2rem', border: '1px solid #e2e8f0', borderTop: `4px solid ${s.color}` }}>
            <div style={{ fontSize: '1.8rem', fontWeight: 800, color: s.color }}>{s.value}</div>
            <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Tab nav */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <button className={`btn ${tab === 'orders' ? 'btn-primary' : 'btn-neutral'}`} onClick={() => setTab('orders')}>
          🍽 Order Queue
        </button>
        <button className={`btn ${tab === 'queue' ? 'btn-primary' : 'btn-neutral'}`} onClick={() => setTab('queue')}>
          📋 Station View
        </button>
      </div>

      {/* Order Queue Tab */}
      {tab === 'orders' && (
        <div className="card">
          <h2>Kitchen Orders</h2>
          {kitchenOrders.length === 0 ? (
            <p className="empty">No active orders. Great job! 🎉</p>
          ) : (
            <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
              {kitchenOrders.map(order => {
                const isUrgent = Math.floor((Date.now() - new Date(order.created_at)) / 60000) > 15
                const borderColor = order.status === 'placed' ? '#f59e0b'
                  : order.status === 'accepted' ? '#8b5cf6'
                  : order.status === 'ready' ? '#22c55e'
                  : '#3b82f6'
                return (
                  <div
                    key={order.id}
                    style={{
                      border: `2px solid ${borderColor}`,
                      borderRadius: 12,
                      padding: '1rem',
                      background: '#fff',
                      position: 'relative',
                    }}
                  >
                    {isUrgent && (
                      <span style={{
                        position: 'absolute', top: 8, right: 8,
                        background: '#dc2626', color: '#fff',
                        fontSize: '0.65rem', fontWeight: 700,
                        borderRadius: 99, padding: '0.15rem 0.5rem',
                        letterSpacing: '0.05em',
                      }}>URGENT</span>
                    )}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                      <strong style={{ fontSize: '1.1rem' }}>Order #{order.id}</strong>
                      <span className={`badge ${order.status === 'placed' ? 'badge-yellow' : order.status === 'ready' ? 'badge-green' : order.status === 'accepted' ? 'badge-blue' : 'badge-blue'}`}>
                        {order.status}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.5rem' }}>
                      Table {order.table_id || '?'} · {timeSince(order.created_at)}
                    </div>

                    {/* Item list with NAMES */}
                    <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '0.5rem', marginBottom: '0.75rem' }}>
                      {order.items?.length > 0 ? order.items.map((item, i) => (
                        <div key={i} style={{ fontSize: '0.9rem', padding: '0.25rem 0', display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
                          <span style={{ fontWeight: 700, color: '#374151', minWidth: 24 }}>{item.quantity}×</span>
                          <span style={{ fontWeight: 500 }}>{item.name || `Item #${item.menu_item_id}`}</span>
                          {item.special_instructions && (
                            <em style={{ color: '#f59e0b', display: 'block', fontSize: '0.75rem', marginTop: '0.1rem' }}>
                              ⚠ {item.special_instructions}
                            </em>
                          )}
                        </div>
                      )) : <p style={{ color: '#94a3b8', fontSize: '0.85rem', margin: 0 }}>No items</p>}
                    </div>

                    {order.special_instructions && (
                      <div style={{ background: '#fffbeb', border: '1px solid #fcd34d', borderRadius: 6, padding: '0.4rem 0.6rem', fontSize: '0.8rem', marginBottom: '0.5rem', color: '#92400e' }}>
                        📝 {order.special_instructions}
                      </div>
                    )}

                    <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                      {order.status === 'placed' && (
                        <button className="btn btn-primary" style={{ fontSize: '0.75rem' }} onClick={() => changeStatus(order.id, 'accepted')}>
                          ✓ Accept Order
                        </button>
                      )}
                      {order.status === 'accepted' && (
                        <button className="btn btn-primary" style={{ fontSize: '0.75rem', background: '#f59e0b', borderColor: '#f59e0b' }} onClick={() => changeStatus(order.id, 'preparing')}>
                          🔥 Start Cooking
                        </button>
                      )}
                      {order.status === 'preparing' && (
                        <button className="btn btn-success" style={{ fontSize: '0.75rem' }} onClick={() => changeStatus(order.id, 'ready')}>
                          ✓ Mark Ready
                        </button>
                      )}
                      {/* Chef can also skip directly */}
                      {isChef() && order.status === 'placed' && (
                        <button className="btn btn-neutral" style={{ fontSize: '0.75rem' }} onClick={() => changeStatus(order.id, 'preparing')}>
                          ⚡ Start Now
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Station Queue Tab */}
      {tab === 'queue' && (
        <div className="card">
          <h2>Station Queue</h2>
          <div className="station-tabs" style={{ marginBottom: '1rem' }}>
            {STATIONS.map(s => (
              <button
                key={s}
                className={`station-tab ${station === s ? 'active' : ''}`}
                onClick={() => setStation(s)}
                style={station === s ? { background: stationColor(s), borderColor: stationColor(s) } : {}}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
                {station === s && queue && (
                  <span style={{ marginLeft: '0.4rem', background: 'rgba(255,255,255,0.3)', borderRadius: 99, padding: '0 0.4rem', fontSize: '0.8rem' }}>
                    {queue.queue_length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {queue && queue.items.length === 0 ? (
            <p className="empty">Queue is clear for {station} station ✓</p>
          ) : queue ? (
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Order</th>
                  <th>Item</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {queue.items.map((item, i) => (
                  <tr key={item.ticket_id}>
                    <td style={{ fontWeight: 700 }}>{i + 1}</td>
                    <td><span className="badge badge-blue">#{item.order_id}</span></td>
                    <td><strong>{item.name}</strong> <small>unit {item.unit_number}</small></td>
                    <td><span className="badge badge-gray">{item.category}</span></td>
                    <td><span className="badge badge-blue">{item.status}</span></td>
                    <td>
                      {item.status === 'queued' && <button className="btn btn-primary" onClick={() => changeTicket(item, 'claim')}>Claim</button>}
                      {item.status === 'claimed' && item.claimed_by_me && <button className="btn btn-primary" onClick={() => changeTicket(item, 'start')}>Start</button>}
                      {item.status === 'processing' && item.claimed_by_me && <button className="btn btn-success" onClick={() => changeTicket(item, 'complete')}>Complete</button>}
                      {['claimed', 'processing'].includes(item.status) && item.claimed_by_me && <button className="btn btn-neutral" onClick={() => changeTicket(item, 'release')}>Release</button>}
                      {['claimed', 'processing'].includes(item.status) && !item.claimed_by_me && <span>Claimed by another staff member</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="empty">Loading…</p>
          )}
        </div>
      )}
    </div>
  )
}
