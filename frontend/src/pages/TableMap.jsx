import { useState, useEffect, useCallback } from 'react'
import { fetchTables, fetchAllocation, fetchCombine } from '../api'

const statusClass = (status) =>
  ({ available: 'table-available', occupied: 'table-occupied', reserved: 'table-reserved' }[status] || 'table-available')

export default function TableMap() {
  const [tables, setTables] = useState([])
  const [allocation, setAllocation] = useState(null)
  const [partySize, setPartySize] = useState(4)
  const [combine, setCombine] = useState(null)
  const [error, setError] = useState('')

  const loadTables = useCallback(async () => {
    try { setTables(await fetchTables()) } catch (e) { setError(String(e)) }
  }, [])

  useEffect(() => { loadTables() }, [loadTables])

  const runAllocation = async () => {
    setError('')
    setAllocation(null)
    try { setAllocation(await fetchAllocation()) } catch (e) { setError(String(e)) }
  }

  const runCombine = async () => {
    setError('')
    setCombine(null)
    try { setCombine(await fetchCombine(partySize)) } catch (e) { setError(String(e)) }
  }

  return (
    <div className="page">
      <h1>Table Map</h1>

      {/* Grid */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <h2 style={{ margin: 0 }}>Floor Plan ({tables.length} tables)</h2>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn btn-neutral" onClick={loadTables}>↻ Refresh</button>
            <button className="btn btn-success" onClick={runAllocation}>Run Allocator</button>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
          <span>🟢 Available</span><span>🟡 Reserved</span><span>🔴 Occupied</span>
        </div>
        {tables.length === 0 ? (
          <p className="empty">No tables found — add some via the API or Swagger at /docs</p>
        ) : (
          <div className="table-grid">
            {tables.map((t) => (
              <div key={t.id} className={`table-cell ${statusClass(t.status)}`}>
                <div>T{t.number}</div>
                <div style={{ fontSize: '0.75rem', fontWeight: 400, marginTop: '0.25rem' }}>
                  Cap: {t.capacity}
                </div>
                <div style={{ fontSize: '0.7rem', marginTop: '0.15rem', opacity: 0.8 }}>
                  {t.status}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Allocation result */}
      {allocation && (
        <div className="card">
          <h2>Allocation Plan</h2>
          {allocation.assignments?.length === 0 && allocation.unassigned?.length === 0 ? (
            <p className="empty">No pending reservations to allocate</p>
          ) : (
            <>
              {allocation.assignments?.length > 0 && (
                <>
                  <p style={{ marginBottom: '0.5rem', color: '#276749', fontWeight: 600 }}>
                    ✓ {allocation.assignments.length} reservation(s) assigned
                  </p>
                  <table>
                    <thead><tr><th>Reservation ID</th><th>Table ID</th></tr></thead>
                    <tbody>
                      {allocation.assignments.map((a) => (
                        <tr key={a.reservation_id}>
                          <td>#{a.reservation_id}</td>
                          <td>Table #{a.table_id}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
              {allocation.unassigned?.length > 0 && (
                <p className="mt1" style={{ color: '#c53030' }}>
                  ✗ Unassigned reservations: {allocation.unassigned.join(', ')}
                </p>
              )}
            </>
          )}
        </div>
      )}

      {/* Combine tables */}
      <div className="card">
        <h2>Combine Tables for Large Party</h2>
        <div className="row">
          <div className="field">
            <label>Party Size</label>
            <input type="number" min="1" value={partySize} onChange={(e) => setPartySize(Number(e.target.value))} />
          </div>
          <button className="btn btn-primary" onClick={runCombine} style={{ alignSelf: 'flex-end' }}>
            Find Groups
          </button>
        </div>
        {combine && (
          <div className="mt1">
            {combine.viable_groups?.length === 0 ? (
              <p className="empty">No table groups can seat {combine.party_size} guests</p>
            ) : (
              <table>
                <thead><tr><th>Table Numbers</th><th>Total Capacity</th><th>Can Seat?</th></tr></thead>
                <tbody>
                  {combine.viable_groups.map((g, i) => (
                    <tr key={i}>
                      <td>{g.table_numbers.map((n) => `T${n}`).join(' + ')}</td>
                      <td>{g.total_capacity} seats</td>
                      <td>
                        <span className={`badge ${g.can_seat_party ? 'badge-green' : 'badge-red'}`}>
                          {g.can_seat_party ? 'Yes ✓' : 'No ✗'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {error && <p className="error">{error}</p>}
    </div>
  )
}
