import { useState, useEffect, useCallback } from 'react'
import { fetchKitchenQueue } from '../api'

const STATIONS = ['grill', 'dessert', 'drinks', 'sides']

export default function KitchenView() {
  const [station, setStation] = useState('grill')
  const [queue, setQueue] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const data = await fetchKitchenQueue(station)
      setQueue(data)
    } catch (e) {
      setError(String(e))
    }
  }, [station])

  useEffect(() => { load() }, [load])

  return (
    <div className="page">
      <h1>Kitchen View</h1>
      <div className="station-tabs">
        {STATIONS.map((s) => (
          <button
            key={s}
            className={`station-tab ${station === s ? 'active' : ''}`}
            onClick={() => setStation(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <h2 style={{ margin: 0, textTransform: 'capitalize' }}>
            {station} Station
            {queue && (
              <span className="badge badge-blue" style={{ marginLeft: '0.5rem' }}>
                {queue.queue_length} item{queue.queue_length !== 1 ? 's' : ''}
              </span>
            )}
          </h2>
          <button className="btn btn-neutral" onClick={load}>↻ Refresh</button>
        </div>

        {error && <p className="error">{error}</p>}

        {queue && queue.items.length === 0 ? (
          <p className="empty">Queue is empty for {station} station</p>
        ) : queue ? (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Order</th>
                <th>Item</th>
                <th>Category</th>
                <th>Station</th>
              </tr>
            </thead>
            <tbody>
              {queue.items.map((item, i) => (
                <tr key={i}>
                  <td>{i + 1}</td>
                  <td>
                    <span className="badge badge-blue">#{item.order_id}</span>
                  </td>
                  <td><strong>{item.name}</strong></td>
                  <td>
                    <span className="badge badge-gray">{item.category}</span>
                  </td>
                  <td style={{ textTransform: 'capitalize' }}>{item.station}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="empty">Loading…</p>
        )}
      </div>

      <p style={{ fontSize: '0.8rem', color: '#a0aec0' }}>
        Items are routed here when an order is created. Use POST /orders (requires staff login) to add items.
      </p>
    </div>
  )
}
