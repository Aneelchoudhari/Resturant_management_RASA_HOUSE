import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, register } from '../api'

export default function Login() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'staff' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        const data = await login(form.email, form.password)
        localStorage.setItem('token', data.access_token)
        navigate('/waitlist')
      } else {
        await register({ name: form.name, email: form.email, password: form.password, role: form.role })
        setMode('login')
        setError('Account created — please log in.')
      }
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page" style={{ maxWidth: 420, marginTop: '4rem' }}>
      <div className="card">
        <h1 style={{ marginBottom: '1.5rem' }}>
          {mode === 'login' ? 'Staff Login' : 'Create Account'}
        </h1>
        <form onSubmit={submit}>
          {mode === 'register' && (
            <div className="field">
              <label>Name</label>
              <input value={form.name} onChange={set('name')} required />
            </div>
          )}
          <div className="field">
            <label>Email</label>
            <input type="email" value={form.email} onChange={set('email')} required />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={form.password} onChange={set('password')} required />
          </div>
          {mode === 'register' && (
            <div className="field">
              <label>Role</label>
              <select value={form.role} onChange={set('role')}>
                <option value="staff">Staff</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          )}
          {error && <p className="error">{error}</p>}
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? 'Please wait…' : mode === 'login' ? 'Login' : 'Register'}
          </button>
        </form>
        <p className="mt2" style={{ fontSize: '0.85rem', color: '#718096', textAlign: 'center' }}>
          {mode === 'login' ? (
            <>No account? <button style={{ background:'none', border:'none', color:'#4299e1', cursor:'pointer' }} onClick={() => setMode('register')}>Register</button></>
          ) : (
            <button style={{ background:'none', border:'none', color:'#4299e1', cursor:'pointer' }} onClick={() => setMode('login')}>← Back to login</button>
          )}
        </p>
      </div>
    </div>
  )
}
