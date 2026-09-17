import { useState } from 'react'
import { fetchOrderHistory } from '../api'

const today = () => new Date().toISOString().slice(0, 10)
const weekAgo = () => {
  const d = new Date()
  d.setDate(d.getDate() - 7)
  return d.toISOString().slice(0, 10)
}

export default function OrderHistory() {
  const [from, setFrom] = useState(weekAgo())
  const [to, setTo] = useState(today())
  const [orders, setOrders] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const search = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await fetchOrderHistory(from || undefined, to || undefined)
      setOrders(data)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  const statusBadge = (status) => ({
    pending: 'badge-yellow',
    preparing: 'badge-blue',
    served: 'badge-green',
    cancelled: 'badge-red',
  }[status] || 'badge-gray')

  return (
    <div className="page">
      <h1>Order History</h1>

      <div className="card">
        <form onSubmit={search}>
          <div className="row">
            <div className="field">
              <label>From Date</label>
              <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
            </div>
            <div className="field">
              <label>To Date</label>
              <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading} style={{ alignSelf: 'flex-end' }}>
              {loading ? 'Searching…' : 'Search'}
            </button>
            <button
              className="btn btn-neutral"
              type="button"
              style={{ alignSelf: 'flex-end' }}
              onClick={() => { setFrom(''); setTo(''); fetchOrderHistory().then(setOrders).catch((e) => setError(String(e))) }}
            >
              All Time
            </button>
          </div>
        </form>
        <p style={{ fontSize: '0.75rem', color: '#a0aec0', marginTop: '0.5rem' }}>
          Uses BST range query O(log n + m) on the backend
        </p>
      </div>

      {error && <p className="error">{error}</p>}

      {orders !== null && (
        <div className="card">
          <h2 style={{ marginBottom: '0.75rem' }}>
            Results — {orders.length} order{orders.length !== 1 ? 's' : ''}
            {from && to && ` (${from} → ${to})`}
          </h2>
          {orders.length === 0 ? (
            <p className="empty">No orders found in this date range</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Table</th>
                  <th>Status</th>
                  <th>Created At</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.id}>
                    <td><span className="badge badge-blue">#{o.id}</span></td>
                    <td>{o.table_id ? `Table #${o.table_id}` : '—'}</td>
                    <td><span className={`badge ${statusBadge(o.status)}`}>{o.status}</span></td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      {new Date(o.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
