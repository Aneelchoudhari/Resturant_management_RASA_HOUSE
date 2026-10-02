import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchTables, fetchActiveOrders, updateTableStatus, updateOrderStatus, createOrder, searchMenu, completePayment } from '../api'

const statusLabel = { available: 'Available', occupied: 'Occupied', reserved: 'Reserved', cleaning: 'Cleaning' }
const statusClass = { available: 'table-available', occupied: 'table-occupied', reserved: 'table-reserved', cleaning: '' }

const orderStatusBadge = (status) => ({
  placed: 'badge-yellow',
  accepted: 'badge-blue',
  preparing: 'badge-blue',
  ready: 'badge-green',
  served: 'badge-gray',
  completed: 'badge-gray',
})[status] || 'badge-gray'

const PAY_METHODS = ['cash', 'card', 'upi']

export default function WaiterDashboard() {
  const [tables, setTables] = useState([])
  const [orders, setOrders] = useState([])
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')

  // New order modal state
  const [showOrderModal, setShowOrderModal] = useState(false)
  const [selectedTable, setSelectedTable] = useState(null)
  const [menuResults, setMenuResults] = useState([])
  const [menuSearch, setMenuSearch] = useState('')
  const [cart, setCart] = useState([])
  const [orderLoading, setOrderLoading] = useState(false)
  const [orderSuccess, setOrderSuccess] = useState(null)
  const orderIdempotencyKey = useRef(null)

  // Payment modal state
  const [showPayModal, setShowPayModal] = useState(false)
  const [payOrder, setPayOrder] = useState(null)
  const [paying, setPaying] = useState({})

  const load = useCallback(async () => {
    setError('')
    try {
      const [t, o] = await Promise.all([fetchTables(), fetchActiveOrders()])
      setTables(t)
      setOrders(o)
    } catch (e) {
      setError(String(e))
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Live menu search for order creation
  useEffect(() => {
    if (!showOrderModal) return
    const timer = setTimeout(async () => {
      try {
        const results = await searchMenu(menuSearch)
        setMenuResults(results.filter(item => item.available))
      } catch { /* ignore */ }
    }, 300)
    return () => clearTimeout(timer)
  }, [menuSearch, showOrderModal])

  const changeTableStatus = async (tableId, status) => {
    setActionError('')
    try {
      await updateTableStatus(tableId, status)
      await load()
    } catch (e) { setActionError(String(e)) }
  }

  const changeOrderStatus = async (orderId, status) => {
    setActionError('')
    try {
      await updateOrderStatus(orderId, status)
      await load()
    } catch (e) { setActionError(String(e)) }
  }

  const openOrderModal = (table) => {
    orderIdempotencyKey.current = null
    setSelectedTable(table)
    setCart([])
    setMenuSearch('')
    setMenuResults([])
    setOrderSuccess(null)
    setShowOrderModal(true)
    searchMenu('').then(r => setMenuResults(r.filter(i => i.available))).catch(() => {})
  }

  const addToCart = (item) => {
    orderIdempotencyKey.current = null
    setCart(curr => {
      const existing = curr.find(e => e.menu_item_id === item.id)
      if (existing) return curr.map(e => e.menu_item_id === item.id ? { ...e, quantity: e.quantity + 1 } : e)
      return [...curr, { menu_item_id: item.id, name: item.name, price: item.price, quantity: 1 }]
    })
  }

  const submitOrder = async () => {
    if (!cart.length) return
    setOrderLoading(true)
    setActionError('')
    try {
      orderIdempotencyKey.current ||= crypto.randomUUID()
      const result = await createOrder({
        table_id: selectedTable.id,
        order_type: 'dine_in',
        items: cart.map(({ menu_item_id, quantity }) => ({ menu_item_id, quantity })),
      }, orderIdempotencyKey.current)
      setOrderSuccess(result.order || result)
      orderIdempotencyKey.current = null
      setCart([])
      // Mark table occupied
      await updateTableStatus(selectedTable.id, 'occupied')
      await load()
    } catch (e) {
      setActionError(String(e))
    } finally {
      setOrderLoading(false)
    }
  }

  const openPayModal = (order) => {
    setPayOrder(order)
    setShowPayModal(true)
  }

  const handlePay = async (orderId, method) => {
    setActionError('')
    setPaying(p => ({ ...p, [orderId]: method }))
    try {
      await completePayment(orderId, method)
      setShowPayModal(false)
      setPayOrder(null)
      await load()
    } catch (e) {
      setActionError(String(e))
    } finally {
      setPaying(p => { const n = { ...p }; delete n[orderId]; return n })
    }
  }

  const activeOrders = orders.filter(o => !['completed', 'cancelled'].includes(o.status))
  const readyOrders = orders.filter(o => o.status === 'ready')
  const servedOrders = orders.filter(o => o.status === 'served' && o.payment_status !== 'paid')

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ margin: 0 }}>Waiter Dashboard</h1>
          <p style={{ color: '#64748b', marginTop: '0.25rem', margin: 0 }}>Manage tables, take orders, serve guests</p>
        </div>
        <button className="btn btn-neutral" onClick={load}>↻ Refresh</button>
      </div>

      {error && <p className="error">{error}</p>}
      {actionError && <p className="error">{actionError}</p>}

      {/* Ready Orders Alert */}
      {readyOrders.length > 0 && (
        <div style={{ background: 'linear-gradient(135deg,#14532d,#166534)', borderRadius: 12, padding: '1rem 1.5rem', marginBottom: '1rem', color: '#fff', display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span style={{ fontSize: '1.5rem' }}>🍽</span>
          <div>
            <strong style={{ fontSize: '1.05rem' }}>{readyOrders.length} order{readyOrders.length !== 1 ? 's' : ''} ready to serve!</strong>
            <p style={{ margin: 0, fontSize: '0.85rem', opacity: 0.85 }}>
              {readyOrders.map(o => `Order #${o.id} — Table ${o.table_id || '?'}`).join(' • ')}
            </p>
          </div>
        </div>
      )}

      {/* Bill Requested Alert */}
      {servedOrders.length > 0 && (
        <div style={{ background: 'linear-gradient(135deg,#1e3a5f,#1d4ed8)', borderRadius: 12, padding: '1rem 1.5rem', marginBottom: '1rem', color: '#fff', display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span style={{ fontSize: '1.5rem' }}>💳</span>
          <div style={{ flex: 1 }}>
            <strong style={{ fontSize: '1.05rem' }}>{servedOrders.length} bill{servedOrders.length !== 1 ? 's' : ''} awaiting payment</strong>
            <p style={{ margin: 0, fontSize: '0.85rem', opacity: 0.85 }}>
              {servedOrders.map(o => `Order #${o.id} — ₹${Number(o.total_amount).toFixed(2)}`).join(' • ')}
            </p>
          </div>
          {servedOrders.map(o => (
            <button key={o.id} className="btn" style={{ background: '#fff', color: '#1d4ed8', fontWeight: 700, fontSize: '0.8rem' }} onClick={() => openPayModal(o)}>
              Pay #{o.id}
            </button>
          ))}
        </div>
      )}

      {/* Floor Map */}
      <section className="card">
        <h2>Floor Map</h2>
        {tables.length === 0 ? (
          <p className="empty">No tables configured yet.</p>
        ) : (
          <div className="table-grid">
            {tables.map(t => (
              <div
                key={t.id}
                className={`table-cell ${statusClass[t.status] || ''}`}
                style={{ cursor: 'default' }}
              >
                <div style={{ fontWeight: 700 }}>T{t.number}</div>
                <div style={{ fontSize: '0.7rem', opacity: 0.8 }}>{t.capacity} seats</div>
                <div style={{ fontSize: '0.65rem', marginTop: '0.2rem', textTransform: 'capitalize' }}>{statusLabel[t.status] || t.status}</div>
                <div style={{ marginTop: '0.4rem', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  {t.status === 'available' && (
                    <button
                      className="btn btn-primary"
                      style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem' }}
                      onClick={() => openOrderModal(t)}
                    >+ Order</button>
                  )}
                  {t.status === 'occupied' && (
                    <button
                      className="btn btn-neutral"
                      style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem' }}
                      onClick={() => changeTableStatus(t.id, 'cleaning')}
                    >Done →</button>
                  )}
                  {t.status === 'cleaning' && (
                    <button
                      className="btn btn-neutral"
                      style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem' }}
                      onClick={() => changeTableStatus(t.id, 'available')}
                    >✓ Clean</button>
                  )}
                  {t.status === 'reserved' && (
                    <button
                      className="btn btn-neutral"
                      style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem' }}
                      onClick={() => changeTableStatus(t.id, 'occupied')}
                    >Seat →</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Active Orders */}
      <section className="card" style={{ marginTop: '1.5rem' }}>
        <h2>Active Orders ({activeOrders.length})</h2>
        {activeOrders.length === 0 ? (
          <p className="empty">No active orders right now.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Order</th>
                <th>Table</th>
                <th>Items</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {activeOrders.map(o => (
                <tr key={o.id}>
                  <td><span className="badge badge-blue">#{o.id}</span></td>
                  <td>{o.table_id ? `T${o.table_id}` : '—'}</td>
                  <td style={{ fontSize: '0.8rem' }}>
                    <div>
                      {o.items?.slice(0, 2).map((item, i) => (
                        <div key={i}>{item.quantity}× {item.name || `Item #${item.menu_item_id}`}</div>
                      ))}
                      {(o.items?.length || 0) > 2 && <div style={{ color: '#94a3b8' }}>+{o.items.length - 2} more</div>}
                    </div>
                    <div style={{ color: '#64748b', marginTop: '0.2rem' }}>₹{Number(o.total_amount).toFixed(0)}</div>
                  </td>
                  <td><span className={`badge ${orderStatusBadge(o.status)}`}>{o.status}</span></td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                      {o.status === 'ready' && (
                        <button className="btn btn-success" style={{ fontSize: '0.75rem' }}
                          onClick={() => changeOrderStatus(o.id, 'served')}>✓ Served</button>
                      )}
                      {o.status === 'served' && o.payment_status !== 'paid' && (
                        <button className="btn btn-primary" style={{ fontSize: '0.75rem' }}
                          onClick={() => openPayModal(o)}>💳 Bill</button>
                      )}
                      {['placed', 'accepted'].includes(o.status) && (
                        <button className="btn btn-neutral" style={{ fontSize: '0.75rem', color: '#ef4444' }}
                          onClick={() => changeOrderStatus(o.id, 'cancelled')}>Cancel</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* New Order Modal */}
      {showOrderModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
          <div style={{ background: '#fff', borderRadius: 16, padding: '1.5rem', maxWidth: 600, width: '100%', maxHeight: '85vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2 style={{ margin: 0 }}>New Order — Table {selectedTable?.number}</h2>
              <button onClick={() => setShowOrderModal(false)} style={{ background: 'none', border: 'none', fontSize: '1.3rem', cursor: 'pointer', color: '#6b7280' }}>✕</button>
            </div>

            {orderSuccess ? (
              <div style={{ background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 8, padding: '1rem' }}>
                <p style={{ color: '#166534', fontWeight: 700, margin: 0 }}>✓ Order #{orderSuccess.id} sent to kitchen!</p>
                <p style={{ color: '#166534', margin: '0.25rem 0 0' }}>Status: {orderSuccess.status} · ₹{Number(orderSuccess.total_amount).toFixed(2)}</p>
                <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={() => setShowOrderModal(false)}>Close</button>
              </div>
            ) : (
              <>
                <input
                  placeholder="Search menu items…"
                  value={menuSearch}
                  onChange={e => setMenuSearch(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem 0.75rem', border: '1px solid #e2e8f0', borderRadius: 8, marginBottom: '0.75rem', boxSizing: 'border-box' }}
                />
                <div style={{ maxHeight: 200, overflowY: 'auto', marginBottom: '1rem', border: '1px solid #e2e8f0', borderRadius: 8 }}>
                  {menuResults.map(item => (
                    <div
                      key={item.id}
                      style={{ padding: '0.6rem 0.75rem', cursor: 'pointer', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                      onClick={() => addToCart(item)}
                    >
                      <div>
                        <span style={{ fontWeight: 500 }}>{item.name}</span>
                        {item.category && <span style={{ fontSize: '0.75rem', color: '#94a3b8', marginLeft: '0.4rem' }}>{item.category}</span>}
                      </div>
                      <span style={{ color: '#64748b', fontSize: '0.85rem' }}>₹{item.price} <span style={{ color: '#22c55e', fontSize: '0.8rem' }}>+ Add</span></span>
                    </div>
                  ))}
                  {menuResults.length === 0 && <p style={{ padding: '0.75rem', color: '#94a3b8', margin: 0 }}>No items found</p>}
                </div>

                {cart.length > 0 && (
                  <>
                    <h3 style={{ marginBottom: '0.5rem' }}>Order</h3>
                    {cart.map(item => (
                      <div key={item.menu_item_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.4rem 0', borderBottom: '1px solid #f1f5f9' }}>
                        <span>{item.name}</span>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                          <button onClick={() => { orderIdempotencyKey.current = null; setCart(c => c.map(e => e.menu_item_id === item.menu_item_id ? { ...e, quantity: Math.max(1, e.quantity - 1) } : e)) }} style={{ background: '#f1f5f9', border: 'none', width: 28, height: 28, borderRadius: 6, cursor: 'pointer', fontWeight: 700 }}>−</button>
                          <span style={{ fontFamily: 'monospace', minWidth: 20, textAlign: 'center' }}>{item.quantity}</span>
                          <button onClick={() => { orderIdempotencyKey.current = null; setCart(c => c.map(e => e.menu_item_id === item.menu_item_id ? { ...e, quantity: e.quantity + 1 } : e)) }} style={{ background: '#f1f5f9', border: 'none', width: 28, height: 28, borderRadius: 6, cursor: 'pointer', fontWeight: 700 }}>+</button>
                          <span style={{ color: '#64748b', minWidth: 60, textAlign: 'right' }}>₹{(item.price * item.quantity).toFixed(0)}</span>
                          <button onClick={() => { orderIdempotencyKey.current = null; setCart(c => c.filter(e => e.menu_item_id !== item.menu_item_id)) }} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '1rem' }}>✕</button>
                        </div>
                      </div>
                    ))}
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem 0', fontWeight: 700, borderTop: '2px solid #e2e8f0', marginTop: '0.5rem' }}>
                      <span>Total</span>
                      <span>₹{cart.reduce((s, i) => s + i.price * i.quantity, 0).toFixed(2)}</span>
                    </div>
                    {actionError && <p className="error">{actionError}</p>}
                    <button
                      className="btn btn-primary"
                      style={{ width: '100%', marginTop: '0.5rem' }}
                      onClick={submitOrder}
                      disabled={orderLoading}
                    >
                      {orderLoading ? 'Sending to kitchen…' : 'Send to Kitchen →'}
                    </button>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Payment Modal */}
      {showPayModal && payOrder && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
          <div style={{ background: '#fff', borderRadius: 16, padding: '1.5rem', maxWidth: 400, width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2 style={{ margin: 0 }}>Process Bill — Order #{payOrder.id}</h2>
              <button onClick={() => setShowPayModal(false)} style={{ background: 'none', border: 'none', fontSize: '1.3rem', cursor: 'pointer', color: '#6b7280' }}>✕</button>
            </div>
            <div style={{ background: '#f8fafc', borderRadius: 8, padding: '1rem', marginBottom: '1rem' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#1d4ed8' }}>₹{Number(payOrder.total_amount).toFixed(2)}</div>
              <div style={{ color: '#64748b', fontSize: '0.85rem' }}>Table {payOrder.table_id || '?'} · {payOrder.items?.length || 0} items</div>
              {payOrder.items?.map((item, i) => (
                <div key={i} style={{ fontSize: '0.85rem', padding: '0.2rem 0' }}>{item.quantity}× {item.name || `Item #${item.menu_item_id}`}</div>
              ))}
            </div>
            {actionError && <p className="error">{actionError}</p>}
            <p style={{ color: '#374151', fontWeight: 600, marginBottom: '0.5rem' }}>Select payment method:</p>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {PAY_METHODS.map(method => (
                <button
                  key={method}
                  className="btn btn-primary"
                  style={{ flex: 1, textTransform: 'uppercase', fontSize: '0.85rem', letterSpacing: '0.05em' }}
                  onClick={() => handlePay(payOrder.id, method)}
                  disabled={!!paying[payOrder.id]}
                >
                  {paying[payOrder.id] === method ? 'Processing…' : method}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
