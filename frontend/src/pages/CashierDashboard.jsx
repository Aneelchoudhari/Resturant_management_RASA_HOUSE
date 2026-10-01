import { useState, useEffect, useCallback } from 'react'
import { fetchActiveOrders, fetchOrderHistory, completePayment, updateOrderStatus } from '../api'

const PAY_METHODS = ['cash', 'card', 'upi']

/**
 * Calculate the loyalty discount that will be applied at checkout.
 * The backend applies: every 100 points = ₹100 off (rounded down to nearest 100 pts used).
 * This client-side preview matches the backend logic exactly.
 */
function calcLoyaltyDiscount(loyaltyPoints, totalAmount) {
  if (!loyaltyPoints || loyaltyPoints < 100) return { discount: 0, pointsUsed: 0 }
  const discountUnits = Math.floor(loyaltyPoints / 100)
  const maxDiscount = discountUnits * 100
  const actualDiscount = Math.min(maxDiscount, totalAmount)
  const pointsUsed = Math.floor(actualDiscount / 100) * 100
  return { discount: pointsUsed, pointsUsed }
}

export default function CashierDashboard() {
  const [orders, setOrders] = useState([])
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [paying, setPaying] = useState({})  // orderId -> method being processed
  const [tab, setTab] = useState('active')
  const [customers, setCustomers] = useState({})  // customer_id -> customer obj (fetched lazily via admin endpoint)

  const load = useCallback(async () => {
    setError('')
    try {
      const active = await fetchActiveOrders()
      setOrders(active)
    } catch (e) { setError(String(e)) }
  }, [])

  useEffect(() => { load() }, [load])

  const handlePay = async (orderId, method) => {
    setActionError('')
    setPaying(p => ({ ...p, [orderId]: method }))
    try {
      await completePayment(orderId, method)
      await load()
    } catch (e) {
      setActionError(String(e))
    } finally {
      setPaying(p => { const n = { ...p }; delete n[orderId]; return n })
    }
  }

  const servedOrders = orders.filter(o => o.status === 'served' && o.payment_status !== 'paid')
  const pendingOrders = orders.filter(o => ['placed', 'accepted', 'preparing', 'ready'].includes(o.status))

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ margin: 0 }}>Cashier Station</h1>
          <p style={{ color: '#64748b', margin: '0.25rem 0 0' }}>Process payments and close bills</p>
        </div>
        <button className="btn btn-neutral" onClick={load}>↻ Refresh</button>
      </div>

      {error && <p className="error">{error}</p>}
      {actionError && <p className="error">{actionError}</p>}

      {/* Loyalty discount info banner */}
      <div style={{ background: 'linear-gradient(135deg,#7c3aed,#4f46e5)', borderRadius: 12, padding: '0.75rem 1.25rem', marginBottom: '1.5rem', color: '#fff', fontSize: '0.88rem' }}>
        <strong>💎 Loyalty Discount</strong> — Customers earn points on VIP bookings (+20 pts) and reservations (+10 pts).
        Every 100 points = ₹100 discount applied automatically at checkout.
      </div>

      {/* Payment alerts */}
      {servedOrders.length > 0 && (
        <div style={{ background: 'linear-gradient(135deg,#1e3a5f,#1d4ed8)', borderRadius: 12, padding: '1rem 1.5rem', marginBottom: '1.5rem', color: '#fff' }}>
          <strong>{servedOrders.length} order{servedOrders.length !== 1 ? 's' : ''} awaiting payment</strong>
          <p style={{ margin: '0.25rem 0 0', opacity: 0.8, fontSize: '0.85rem' }}>
            {servedOrders.map(o => `Order #${o.id} — ₹${Number(o.total_amount).toFixed(2)}`).join(' · ')}
          </p>
        </div>
      )}

      {/* Tab nav */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <button className={`btn ${tab === 'active' ? 'btn-primary' : 'btn-neutral'}`} onClick={() => setTab('active')}>
          💳 Pending Payment ({servedOrders.length})
        </button>
        <button className={`btn ${tab === 'all' ? 'btn-primary' : 'btn-neutral'}`} onClick={() => setTab('all')}>
          📋 All Active Orders
        </button>
      </div>

      {tab === 'active' && (
        <div className="card">
          <h2>Bills Awaiting Payment</h2>
          {servedOrders.length === 0 ? (
            <p className="empty">No pending bills right now.</p>
          ) : (
            servedOrders.map(order => {
              // Loyalty discount preview (customer_id is in order data)
              // We show the discount that will be applied; exact amount computed by backend
              const hasCustomer = !!order.customer_id

              return (
                <div key={order.id} style={{ border: '2px solid #3b82f6', borderRadius: 12, padding: '1rem 1.25rem', marginBottom: '1rem', background: '#fff' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                    <div>
                      <strong style={{ fontSize: '1.1rem' }}>Order #{order.id}</strong>
                      <div style={{ color: '#64748b', fontSize: '0.85rem' }}>Table {order.table_id || '?'} · {order.items?.length ?? 0} items</div>
                      {hasCustomer && (
                        <div style={{ fontSize: '0.78rem', color: '#7c3aed', marginTop: '0.2rem' }}>
                          💎 Customer account linked — loyalty discount applied automatically at payment
                        </div>
                      )}
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#1d4ed8' }}>₹{Number(order.total_amount).toFixed(2)}</div>
                      {hasCustomer && (
                        <div style={{ fontSize: '0.75rem', color: '#7c3aed' }}>
                          Discount deducted from bill
                        </div>
                      )}
                    </div>
                  </div>
                  <div style={{ marginTop: '0.5rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '0.4rem' }}>Select payment method:</div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      {PAY_METHODS.map(method => (
                        <button
                          key={method}
                          className="btn btn-primary"
                          style={{ flex: 1, textTransform: 'uppercase', fontSize: '0.8rem', letterSpacing: '0.05em' }}
                          onClick={() => handlePay(order.id, method)}
                          disabled={!!paying[order.id]}
                        >
                          {paying[order.id] === method ? 'Processing…' : method}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}

      {tab === 'all' && (
        <div className="card">
          <h2>All Active Orders</h2>
          {orders.length === 0 ? <p className="empty">No active orders.</p> : (
            <table>
              <thead>
                <tr><th>Order</th><th>Table</th><th>Status</th><th>Total</th><th>Payment</th></tr>
              </thead>
              <tbody>
                {orders.map(o => (
                  <tr key={o.id}>
                    <td><span className="badge badge-blue">#{o.id}</span></td>
                    <td>{o.table_id ? `T${o.table_id}` : '—'}</td>
                    <td><span className={`badge ${o.status === 'served' ? 'badge-green' : 'badge-blue'}`}>{o.status}</span></td>
                    <td>₹{Number(o.total_amount).toFixed(2)}{o.customer_id && <span title="Loyalty discount applies" style={{ marginLeft: '0.3rem', color: '#7c3aed' }}>💎</span>}</td>
                    <td>
                      {o.payment_status === 'paid'
                        ? <span className="badge badge-green">Paid</span>
                        : o.status === 'served'
                          ? <div style={{ display: 'flex', gap: '0.3rem' }}>
                              {PAY_METHODS.map(m => (
                                <button key={m} className="btn btn-primary" style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem', textTransform: 'uppercase' }}
                                  onClick={() => handlePay(o.id, m)} disabled={!!paying[o.id]}>
                                  {m}
                                </button>
                              ))}
                            </div>
                          : <span className="badge badge-gray">Awaiting</span>
                      }
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
