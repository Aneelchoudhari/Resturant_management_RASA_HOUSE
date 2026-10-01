import { useEffect, useState } from 'react'
import { createStaff, fetchStaff, updateStaff, deleteStaff } from '../api'

const roles = [
  { value: 'manager', label: 'Manager' },
  { value: 'waiter', label: 'Waiter' },
  { value: 'chef', label: 'Chef' },
  { value: 'inventory', label: 'Kitchen Staff' },
  { value: 'cashier', label: 'Cashier' },
  { value: 'receptionist', label: 'Host / Floor Manager' },
]

export default function StaffManagement() {
  const [staff, setStaff] = useState([])
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'waiter' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => { fetchStaff().then(setStaff).catch((err) => setError(String(err))) }, [])

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      const created = await createStaff(form)
      setStaff((current) => [...current, created])
      setForm({ name: '', email: '', password: '', role: 'waiter' })
      setMessage(`Account created for ${created.email}. Give these credentials to the employee securely.`)
    } catch (err) {
      setError(String(err))
    }
  }

  const changeStatus = async (member) => {
    try {
      const updated = await updateStaff(member.id, { active: !member.active })
      setStaff((current) => current.map((item) => item.id === updated.id ? updated : item))
    } catch (err) { setError(String(err)) }
  }

  const resetPassword = async (member) => {
    const password = window.prompt(`New temporary password for ${member.name} (8+ characters):`)
    if (!password) return
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    try {
      await updateStaff(member.id, { password })
      setMessage(`Password reset for ${member.email}. Share it securely.`)
    } catch (err) { setError(String(err)) }
  }

  const handleDelete = async (member) => {
    const confirmed = window.confirm(
      `Permanently delete ${member.name} (${member.email})?\n\nThis action cannot be undone.`
    )
    if (!confirmed) return
    setError('')
    setMessage('')
    try {
      await deleteStaff(member.id)
      setStaff((current) => current.filter((item) => item.id !== member.id))
      setMessage(`Staff account for ${member.email} has been permanently deleted.`)
    } catch (err) { setError(String(err)) }
  }

  return (
    <div className="page">
      <h1>Employee Accounts</h1>
      <div className="card">
        <h2>Create staff account</h2>
        <p style={{ color: '#475569', marginBottom: '1rem' }}>Only an authenticated administrator can provision employee credentials.</p>
        <form onSubmit={submit}>
          <div className="row"><div className="field"><label>Name</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></div><div className="field"><label>Employee email</label><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></div></div>
          <div className="row"><div className="field"><label>Temporary password</label><input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} minLength="8" required /></div><div className="field"><label>Role</label><select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>{roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}</select></div></div>
          {message && <p className="success">{message}</p>}{error && <p className="error">{error}</p>}
          <button className="btn btn-primary" type="submit">Create employee account</button>
        </form>
      </div>
      <div className="card">
        <h2>Provisioned employees</h2>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {staff.map((member) => (
              <tr key={member.id}>
                <td>{member.name}</td>
                <td>{member.email}</td>
                <td><span className="badge badge-blue">{member.role}</span></td>
                <td><span className={`badge ${member.active ? 'badge-green' : 'badge-gray'}`}>{member.active ? 'Active' : 'Inactive'}</span></td>
                <td style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                  <button className="btn btn-neutral" onClick={() => changeStatus(member)}>
                    {member.active ? 'Deactivate' : 'Activate'}
                  </button>
                  {member.active && (
                    <button className="btn btn-neutral" onClick={() => resetPassword(member)}>
                      Reset password
                    </button>
                  )}
                  <button
                    className="btn btn-neutral"
                    style={{ color: '#ef4444', borderColor: '#ef4444' }}
                    onClick={() => handleDelete(member)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}