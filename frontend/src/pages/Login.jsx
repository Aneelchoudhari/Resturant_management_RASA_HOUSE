import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { customerLogin, login, registerCustomer } from '../api'
import { getUserRole } from '../auth'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const staffMode = new URLSearchParams(location.search).get('role') === 'staff'
  const selectedStaffRole = new URLSearchParams(location.search).get('staffRole')
  const [mode, setMode] = useState(staffMode ? 'staff-login' : 'customer-login')
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const customerMode = mode.startsWith('customer')
      localStorage.removeItem('token')
      if (mode.endsWith('login')) {
        const data = customerMode
          ? await customerLogin(form.email, form.password)
          : await login(form.email, form.password)
        localStorage.setItem('token', data.access_token)
        if (!customerMode && selectedStaffRole && getUserRole() !== selectedStaffRole) {
          const actualRole = getUserRole()
          localStorage.removeItem('token')
          throw new Error(`This account is assigned to ${actualRole}, not ${selectedStaffRole}.`)
        }
        navigate(customerMode ? '/customer/account' : getUserRole() === 'admin' ? '/admin' : '/staff')
      } else {
        if (customerMode) {
          await registerCustomer({ name: form.name, email: form.email, password: form.password })
          const data = await customerLogin(form.email, form.password)
          localStorage.setItem('token', data.access_token)
          navigate('/customer/account')
          return
        }
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
          {mode === 'customer-login' ? 'Customer Login' : mode === 'staff-login' ? `${selectedStaffRole ? selectedStaffRole[0].toUpperCase() + selectedStaffRole.slice(1) : 'Staff'} Login` : 'Create Account'}
        </h1>
        <form onSubmit={submit}>
          {!mode.endsWith('login') && (
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
          {error && <p className="error">{error}</p>}
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? 'Please wait…' : mode.endsWith('login') ? 'Login' : 'Register'}
          </button>
        </form>
        <p className="mt2" style={{ fontSize: '0.85rem', color: '#718096', textAlign: 'center' }}>
          {mode.endsWith('login') && mode.startsWith('customer') ? (
            <>New here? <button style={{ background:'none', border:'none', color:'#4299e1', cursor:'pointer' }} onClick={() => setMode('customer-register')}>Create account</button></>
          ) : mode === 'staff-login' ? (
            <>Staff accounts are created and issued by an administrator.</>
          ) : (
            <button style={{ background:'none', border:'none', color:'#4299e1', cursor:'pointer' }} onClick={() => setMode(mode.startsWith('customer') ? 'customer-login' : 'staff-login')}>← Back to login</button>
          )}
        </p>
        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', marginTop: '1rem' }}>
          <button className="btn btn-neutral" type="button" onClick={() => setMode('customer-login')}>Customer</button>
          <button className="btn btn-neutral" type="button" onClick={() => setMode('staff-login')}>Staff</button>
        </div>
      </div>
    </div>
  )
}
