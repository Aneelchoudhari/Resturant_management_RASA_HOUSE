import { Link } from 'react-router-dom'

const roles = [
  { key: 'waiter', title: 'Waiter', description: 'Take orders, serve tables, manage guest requests.', accent: 'Terracotta' },
  { key: 'manager', title: 'Manager', description: 'Daily operations, orders, reservations.', accent: 'Amber' },
  { key: 'admin', title: 'Admin', description: 'Full access: staff, menu, settings.', accent: 'Ink' },
  { key: 'chef', title: 'Chef', description: 'Kitchen lead — tickets, station routing, quality.', accent: 'Sage' },
  { key: 'inventory', title: 'Kitchen Staff', description: 'KDS station — prep, cook, mark ready.', accent: 'Green' },
  { key: 'cashier', title: 'Cashier', description: 'Bills, payments, receipts.', accent: 'Blue' },
  { key: 'receptionist', title: 'Host / Floor Manager', description: 'Tables, reservations, and waitlist.', accent: 'Rose' },
]

export default function StaffRoleSelect() {
  return (
    <main className="staff-entry">
      <header className="staff-entry-nav">
        <Link to="/" className="staff-wordmark">RASA<span>HOUSE</span></Link>
        <Link to="/" className="back-link">← Back to restaurant</Link>
      </header>
      <section className="staff-entry-content">
        <p className="eyebrow">Team portal</p>
        <h1>Where do you<br /><em>make things happen?</em></h1>
        <p className="staff-entry-intro">
          Choose your workspace. Your account must be provisioned by an admin for the matching role.
        </p>
        <div className="staff-role-grid">
          {roles.map((role) => (
            <Link
              className="staff-role-card"
              to={`/login?role=staff&staffRole=${role.key}`}
              key={role.key}
            >
              <span className={`role-dot role-dot-${role.key}`} />
              <span className="role-card-copy">
                <strong>{role.title}</strong>
                <small>{role.description}</small>
              </span>
              <span className="role-arrow">↗</span>
            </Link>
          ))}
        </div>
      </section>
      <p className="staff-entry-foot">
        Access is protected by your staff credentials. Contact admin if you do not have an account.
      </p>
    </main>
  )
}
