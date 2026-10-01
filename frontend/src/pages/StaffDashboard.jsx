import { Link } from 'react-router-dom'
import { isAdminUser } from '../auth'

export default function StaffDashboard() {
  return (
    <div className="page">
      <h1>Operations Overview</h1>
      <div className="role-hero">
        <div className="role-card">
          <h3>Waitlist</h3>
          <p>Monitor queue priority, current waits, and guest flow.</p>
          <Link className="btn btn-primary" to="/waitlist">Open Queue</Link>
        </div>

        <div className="role-card">
          <h3>Tables</h3>
          <p>Review seat availability, allocate reservations, and combine groups.</p>
          <Link className="btn btn-primary" to="/tables">View Tables</Link>
        </div>

        <div className="role-card">
          <h3>Kitchen</h3>
          <p>Track station queues and prepare orders in sequence.</p>
          <Link className="btn btn-primary" to="/kitchen">Open Kitchen</Link>
        </div>

        <div className="role-card">
          <h3>Orders & History</h3>
          <p>Review order records and analyze recent restaurant activity.</p>
          <Link className="btn btn-primary" to="/history">View History</Link>
        </div>
      </div>

      <div className="card">
        <h2>Staff Dashboard</h2>
        <p style={{ color: '#475569', lineHeight: 1.6 }}>
          This view is for staff and administrators. It exposes operational tools that support reservations,
          floor management, kitchen routing, and order tracking.
        </p>
      </div>
      {isAdminUser() && <div className="card"><h2>Administrator</h2><p style={{ color: '#475569', lineHeight: 1.6 }}>Only admins can create or remove employee accounts.</p><Link className="btn btn-primary" to="/staff/manage">Manage staff accounts</Link></div>}
    </div>
  )
}
