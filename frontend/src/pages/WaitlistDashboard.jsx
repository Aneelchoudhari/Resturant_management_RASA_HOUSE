import { useState, useEffect, useCallback } from 'react'
import { fetchWaitlist, joinWaitlist } from '../api'

const priorityLabel = (score) => {
  if (score < 500) return { label: 'HIGH', cls: 'priority-high' }
  if (score < 1500) return { label: 'MED', cls: 'priority-medium' }
  return { label: 'LOW', cls: 'priority-low' }
}

export default function WaitlistDashboard() {
  const [queue, setQueue] = useState([])
  const [form, setForm] = useState({ guest_name: '', party_size: 2, priority_tier: 1 })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await fetchWaitlist()
      setQueue(data)
    } catch (e) {
      setError(String(e))
    }
  }, [])

  useEffect(() => { load() }, [load])

  const set = (k) => (e) =>
    setForm((f) => ({ ...f, [k]: k === 'guest_name' ? e.target.value : Number(e.target.value) }))

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await joinWaitlist(form)
      setForm({ guest_name: '', party_size: 2, priority_tier: 1 })
      await load()
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <h1>Waitlist Dashboard</h1>

      {/* Add to waitlist */}
      <div className="card">
        <h2>Add Guest to Queue</h2>
        <form onSubmit={submit}>
          <div className="row">
            <div className="field">
              <label>Guest Name</label>
              <input value={form.guest_name} onChange={set('guest_name')} required />
            </div>
            <div className="field">
              <label>Party Size</label>
              <input type="number" min="1" max="20" value={form.party_size} onChange={set('party_size')} />
            </div>
            <div className="field">
              <label>Priority Tier (1=VIP, 3=Walk-in)</label>
              <select value={form.priority_tier} onChange={set('priority_tier')}>
                <option value={1}>1 — VIP</option>
                <option value={2}>2 — Reservation</option>
                <option value={3}>3 — Walk-in</option>
              </select>
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading} style={{ alignSelf: 'flex-end' }}>
              {loading ? 'Adding…' : 'Join Queue'}
            </button>
          </div>
          {error && <p className="error mt1">{error}</p>}
        </form>
      </div>

      {/* Queue view */}
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
                <th>Tier</th>
                <th>Score</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              {queue.map((entry, i) => {
                const p = priorityLabel(entry.priority_score)
                return (
                  <tr key={entry.id}>
                    <td>#{i + 1}</td>
                    <td>{entry.guest_name}</td>
                    <td>{entry.party_size} pax</td>
                    <td>
                      <span className={`badge ${entry.priority_tier === 1 ? 'badge-green' : entry.priority_tier === 2 ? 'badge-blue' : 'badge-gray'}`}>
                        Tier {entry.priority_tier}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'monospace' }}>{entry.priority_score?.toFixed(0)}</td>
                    <td><span className={p.cls}>{p.label}</span></td>
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
