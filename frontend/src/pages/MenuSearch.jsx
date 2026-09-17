import { useState, useEffect, useRef } from 'react'
import { searchMenu, fetchMenuByCategory } from '../api'

const CATEGORIES = ['mains', 'sides', 'desserts', 'drinks', 'starters']

export default function MenuSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [category, setCategory] = useState('')
  const [error, setError] = useState('')
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
                <div className="meta">
                  <span className="badge badge-blue">{item.category}</span>
                  &nbsp; ${Number(item.price).toFixed(2)}
                </div>
                {item.tags && <div className="meta" style={{ marginTop: '0.2rem' }}>{item.tags}</div>}
              </li>
            ))}
          </ul>
        )}
        <p style={{ fontSize: '0.75rem', color: '#a0aec0', marginTop: '0.75rem' }}>
          {results.length} item{results.length !== 1 ? 's' : ''} — searching via Trie prefix match
        </p>
      </div>
    </div>
  )
}
