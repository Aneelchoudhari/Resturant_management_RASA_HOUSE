import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { isAdminUser, isCustomerUser, isStaffUser, getUserRole, getRoleLabel } from '../auth'

export default function NavBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const role = getUserRole()
  const staffView = isStaffUser()
  const customerAccount = isCustomerUser()
  const isLoggedIn = !!localStorage.getItem('token')

  if (['/', '/staff/select', '/login'].includes(location.pathname)) return null

  const logout = () => {
    localStorage.removeItem('token')
    navigate('/')
  }

  // ── Customer Nav ─────────────────────────────────────────────────────────────
  const customerLinks = (
    <>
      <NavLink to="/customer">Home</NavLink>
      <NavLink to="/customer/menu">Menu</NavLink>
      <NavLink to="/customer/reservation">Reservations</NavLink>
      <NavLink to="/customer/waitlist">Waitlist</NavLink>
      {customerAccount && <NavLink to="/customer/account">My Account</NavLink>}
    </>
  )

  // ── Admin Sidebar ─────────────────────────────────────────────────────────────
  if (isAdminUser()) {
    const adminLinks = [
      ['▦', 'Dashboard', '/admin'],
      ['◷', 'Bookings', '/reservation'],
      ['◉', 'Orders', '/history'],
      ['⌗', 'Tables', '/tables'],
      ['✦', 'Menu & Inventory', '/menu'],
      ['♧', 'Staff', '/staff/manage'],
      ['⌁', 'Kitchen', '/kitchen'],
      ['◌', 'Waitlist', '/waitlist'],
    ]
    return (
      <aside className="admin-sidebar">
        <div className="admin-brand">RASA<span>HOUSE</span><small>ADMIN CONSOLE</small></div>
        <div className="admin-sidebar-label">Workspace</div>
        <div className="admin-sidebar-links">
          {adminLinks.map(([icon, label, to]) => (
            <NavLink to={to} className={({ isActive }) => isActive ? 'active' : ''} key={to}>
              <b>{icon}</b>{label}
            </NavLink>
          ))}
        </div>
        <div className="admin-sidebar-footer">
          <span className="admin-avatar">A</span>
          <div><strong>Administrator</strong><small>Full access</small></div>
          <button className="sidebar-logout" onClick={logout} title="Log out">↗</button>
        </div>
      </aside>
    )
  }

  // ── Role-Specific Staff Navs ──────────────────────────────────────────────────
  let staffLinks = null

  if (role === 'waiter') {
    staffLinks = (
      <>
        <NavLink to="/staff">My Tables</NavLink>
        <NavLink to="/menu">Menu</NavLink>
        <NavLink to="/history">Orders</NavLink>
      </>
    )
  } else if (role === 'chef' || role === 'inventory') {
    staffLinks = (
      <>
        <NavLink to="/kitchen">Kitchen</NavLink>
        <NavLink to="/menu">Menu</NavLink>
      </>
    )
  } else if (role === 'receptionist') {
    staffLinks = (
      <>
        <NavLink to="/staff">Floor Manager</NavLink>
        <NavLink to="/tables">Tables</NavLink>
        <NavLink to="/waitlist">Waitlist</NavLink>
        <NavLink to="/reservation">Reservations</NavLink>
      </>
    )
  } else if (role === 'cashier') {
    staffLinks = (
      <>
        <NavLink to="/staff">Billing</NavLink>
        <NavLink to="/history">Orders</NavLink>
      </>
    )
  } else if (role === 'manager') {
    staffLinks = (
      <>
        <NavLink to="/staff">Overview</NavLink>
        <NavLink to="/waitlist">Waitlist</NavLink>
        <NavLink to="/tables">Tables</NavLink>
        <NavLink to="/kitchen">Kitchen</NavLink>
        <NavLink to="/history">Orders</NavLink>
        <NavLink to="/menu">Menu</NavLink>
        <NavLink to="/reservation">Reservations</NavLink>
      </>
    )
  } else if (staffView) {
    // Generic staff fallback
    staffLinks = (
      <>
        <NavLink to="/staff">Overview</NavLink>
        <NavLink to="/menu">Menu</NavLink>
        <NavLink to="/history">Orders</NavLink>
      </>
    )
  }

  return (
    <nav className={staffView ? 'staff-nav' : 'customer-nav'}>
      <span className="brand">
        {staffView
          ? `🍽\u00a0${getRoleLabel()}`
          : <><strong style={{ letterSpacing: '0.06em' }}>RASA</strong><span style={{ color: '#d8a449', letterSpacing: '0.06em' }}>HOUSE</span></>}
      </span>
      {staffView ? staffLinks : customerLinks}
      {isLoggedIn ? (
        <button className="logout" onClick={logout}>Logout</button>
      ) : null}
    </nav>
  )
}
