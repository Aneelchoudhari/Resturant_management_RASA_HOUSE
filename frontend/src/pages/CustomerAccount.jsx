import { useEffect, useState } from 'react'
import { fetchCustomerAccount, fetchCustomerOrders, fetchCustomerReservations } from '../api'

const statusBadge = (status) => ({
  pending: 'badge-yellow',
  confirmed: 'badge-green',
  cancelled: 'badge-gray',
  completed: 'badge-blue',
})[status] || 'badge-gray'

const orderStatusBadge = (status) => ({
  placed: 'badge-yellow',
  accepted: 'badge-blue',
  preparing: 'badge-blue',
  ready: 'badge-green',
  served: 'badge-green',
  completed: 'badge-gray',
  cancelled: 'badge-gray',
})[status] || 'badge-gray'

export default function CustomerAccount() {
  const [account, setAccount] = useState(null)
  const [reservations, setReservations] = useState([])
  const [orders, setOrders] = useState([])
  const [error, setError] = useState('')
  const [expandedOrder, setExpandedOrder] = useState(null)

  useEffect(() => {
    Promise.all([fetchCustomerAccount(), fetchCustomerReservations(), fetchCustomerOrders()])
      .then(([profile, history, orderHistory]) => {
        setAccount(profile)
        setReservations(history)
        setOrders(orderHistory)
      })
      .catch((err) => setError(String(err)))
  }, [])

  return (
    <div className="page">
      <h1>My Dining Account</h1>
      {error && <p className="error">{error}</p>}
      {account && (
        <div className="role-hero">
          <div className="role-card">
            <h3>{account.name}</h3>
            <p style={{ color: '#64748b' }}>{account.email}</p>
          </div>
          <div className="role-card">
            <h3 style={{ color: '#f59e0b' }}>⭐ {account.loyalty_points} points</h3>
            <p style={{ color: '#64748b', fontSize: '0.85rem' }}>Earn 10 points for every reservation made while signed in.</p>
          </div>
        </div>
      )}

      {/* Order History */}
      <div className="card">
        <h2>My Orders</h2>
        {orders.length === 0 ? (
          <p className="empty">You have not placed any orders yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {orders.map((order) => (
              <div key={order.id} style={{ border: '1px solid #e2e8f0', borderRadius: 10, overflow: 'hidden' }}>
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', cursor: 'pointer', background: '#f8fafc' }}
                  onClick={() => setExpandedOrder(expandedOrder === order.id ? null : order.id)}
                >
                  <div>
                    <strong>Order #{order.id}</strong>
                    <span style={{ marginLeft: '0.75rem', color: '#64748b', fontSize: '0.85rem' }}>
                      {new Date(order.created_at).toLocaleDateString([], { day: 'numeric', month: 'short', year: 'numeric' })}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                    <span className={`badge ${orderStatusBadge(order.status)}`}>{order.status}</span>
                    <strong>₹{Number(order.total_amount).toFixed(2)}</strong>
                    <span style={{ color: '#94a3b8' }}>{expandedOrder === order.id ? '▲' : '▼'}</span>
                  </div>
                </div>
                {expandedOrder === order.id && (
                  <div style={{ padding: '0.75rem 1rem', borderTop: '1px solid #f1f5f9' }}>
                    {order.items?.length > 0 ? order.items.map((item, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0', fontSize: '0.9rem' }}>
                        <span>{item.quantity}× {item.name || `Item #${item.menu_item_id}`}</span>
                        <span style={{ color: '#64748b' }}>₹{(item.unit_price * item.quantity).toFixed(2)}</span>
                      </div>
                    )) : <p style={{ color: '#94a3b8', margin: 0, fontSize: '0.85rem' }}>No item details available</p>}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Reservation History */}
      <div className="card">
        <h2>My Reservations</h2>
        {reservations.length === 0 ? (
          <p className="empty">Your signed-in reservations will appear here.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Date & Time</th><th>Party Size</th><th>Table</th><th>Status</th></tr>
            </thead>
            <tbody>
              {reservations.map((reservation) => (
                <tr key={reservation.id}>
                  <td>{new Date(reservation.start_time).toLocaleString([], { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
                  <td>{reservation.party_size} guests</td>
                  <td>{reservation.table_id ? `Table ${reservation.table_id}` : 'Unassigned'}</td>
                  <td><span className={`badge ${statusBadge(reservation.status)}`}>{reservation.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
