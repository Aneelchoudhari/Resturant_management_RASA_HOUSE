import { useState, useEffect, useRef } from 'react'
import { createCustomerOrder, searchMenu, fetchMenuByCategory } from '../api'
import { isCustomerUser } from '../auth'

const CATEGORIES = ['mains', 'sides', 'desserts', 'drinks', 'starters']

export default function MenuSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [category, setCategory] = useState('')
  const [error, setError] = useState('')
  const [cart, setCart] = useState([])
  const [orderType, setOrderType] = useState('dine_in')
  const [instructions, setInstructions] = useState('')
  const [orderResult, setOrderResult] = useState(null)
  const [ordering, setOrdering] = useState(false)
  const debounce = useRef(null)

  // Live prefix search — debounced 300ms
  useEffect(() => {
    clearTimeout(debounce.current)
    debounce.current = setTimeout(async () => {
      setError('')
      try {
        const data = await searchMenu(query)
        setResults(data)
      } catch (e) {
        setError(String(e))
      }
    }, 300)
    return () => clearTimeout(debounce.current)
  }, [query])

  const filterByCategory = async (cat) => {
    setError('')
    setCategory(cat)
    setQuery('')
    try {
      const data = await fetchMenuByCategory(cat)
      setResults(data)
    } catch (e) {
      setError(String(e))
    }
  }

  const clearCategory = () => {
    setCategory('')
    setQuery('')
    searchMenu('').then(setResults).catch((e) => setError(String(e)))
  }

  const addToCart = (item) => {
    setCart((current) => {
      const existing = current.find((entry) => entry.menu_item_id === item.id)
      if (existing) {
        return current.map((entry) => entry.menu_item_id === item.id
          ? { ...entry, quantity: entry.quantity + 1 }
          : entry)
      }
      return [...current, { menu_item_id: item.id, name: item.name, price: item.price, quantity: 1 }]
    })
  }

  const updateQuantity = (id, quantity) => {
    setCart((current) => current.map((entry) => entry.menu_item_id === id
      ? { ...entry, quantity: Math.max(1, quantity) }
      : entry))
  }

  const placeOrder = async () => {
    setError('')
    setOrderResult(null)
    setOrdering(true)
    try {
      const order = await createCustomerOrder({
        order_type: orderType,
        special_instructions: instructions || null,
        items: cart.map(({ menu_item_id, quantity }) => ({ menu_item_id, quantity })),
      })
      setOrderResult(order)
      setCart([])
      setInstructions('')
    } catch (e) {
      setError(String(e))
    } finally {
      setOrdering(false)
    }
  }

  const cartTotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0)

  return (
    <div className="page">
      <h1>Menu Search</h1>

      <div className="card">
        <div className="search-wrap">
          <input
            placeholder="Type to search menu items… (Trie autocomplete)"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setCategory('') }}
          />
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              className={`btn ${category === cat ? 'btn-primary' : 'btn-neutral'}`}
              onClick={() => (category === cat ? clearCategory() : filterByCategory(cat))}
            >
              {cat}
            </button>
          ))}
          {category && (
            <button className="btn btn-neutral" onClick={clearCategory}>✕ Clear</button>
          )}
        </div>
        {error && <p className="error">{error}</p>}
        {results.length === 0 ? (
          <p className="empty">{query || category ? 'No items found' : 'Start typing or pick a category'}</p>
        ) : (
          <ul className="results-list">
            {results.map((item) => (
              <li key={item.id} className="result-item">
                <div className="name">{item.name}</div>
                {item.description && <div className="meta">{item.description}</div>}
                <div className="meta">
                  <span className="badge badge-blue">{item.category}</span>
                  &nbsp; ₹{Number(item.price).toFixed(2)}
                  &nbsp; <span className={item.available ? 'badge badge-green' : 'badge badge-red'}>{item.available ? 'Available' : 'Unavailable'}</span>
                </div>
                {item.tags && <div className="meta" style={{ marginTop: '0.2rem' }}>{item.tags}</div>}
                {item.available && <button className="btn btn-primary" style={{ marginTop: '0.65rem' }} onClick={() => addToCart(item)}>Add to cart</button>}
              </li>
            ))}
          </ul>
        )}
        <p style={{ fontSize: '0.75rem', color: '#a0aec0', marginTop: '0.75rem' }}>
          {results.length} item{results.length !== 1 ? 's' : ''} — searching via Trie prefix match
        </p>
      </div>

      {cart.length > 0 && (
        <div className="card">
          <h2>Your Cart</h2>
          {cart.map((item) => (
            <div key={item.menu_item_id} className="row" style={{ marginBottom: '0.5rem' }}>
              <strong style={{ flex: 1 }}>{item.name}</strong>
              <input aria-label={`Quantity for ${item.name}`} type="number" min="1" value={item.quantity} onChange={(e) => updateQuantity(item.menu_item_id, Number(e.target.value))} style={{ width: 72 }} />
              <span>₹{(item.price * item.quantity).toFixed(2)}</span>
            </div>
          ))}
          {isCustomerUser() ? (
            <>
              <div className="row mt1">
                <div className="field"><label>Order Type</label><select value={orderType} onChange={(e) => setOrderType(e.target.value)}><option value="dine_in">Dine-in</option><option value="takeaway">Takeaway</option></select></div>
                <div className="field"><label>Special Instructions</label><input value={instructions} onChange={(e) => setInstructions(e.target.value)} placeholder="Less spicy, no onions..." /></div>
              </div>
              <p className="mt1"><strong>Total: ₹{cartTotal.toFixed(2)}</strong></p>
              <button className="btn btn-success mt1" onClick={placeOrder} disabled={ordering}>{ordering ? 'Placing order…' : 'Place Order'}</button>
            </>
          ) : <p className="error mt1">Please sign in as a customer before placing an order.</p>}
        </div>
      )}

      {orderResult && <div className="card" style={{ borderLeft: '4px solid #48bb78' }}><h2>Order #{orderResult.id} placed</h2><p>Status: {orderResult.status} · Total: ₹{Number(orderResult.total_amount).toFixed(2)}</p></div>}
    </div>
  )
}
