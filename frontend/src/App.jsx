import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import {
  isAdminUser,
  isCustomerUser,
  isStaffUser,
  isKitchenUser,
  isWaiterUser,
  isHostUser,
  isCashierUser,
  getUserRole,
} from './auth'
import NavBar from './components/NavBar'
import Login from './pages/Login'
import WaitlistDashboard from './pages/WaitlistDashboard'
import TableMap from './pages/TableMap'
import MenuSearch from './pages/MenuSearch'
import ReservationForm from './pages/ReservationForm'
import KitchenView from './pages/KitchenView'
import OrderHistory from './pages/OrderHistory'
import CustomerHome from './pages/CustomerHome'
import StaffDashboard from './pages/StaffDashboard'
import CustomerAccount from './pages/CustomerAccount'
import LandingPage from './pages/LandingPage'
import StaffRoleSelect from './pages/StaffRoleSelect'
import StaffManagement from './pages/StaffManagement'
import AdminDashboard from './pages/AdminDashboard'
import WaiterDashboard from './pages/WaiterDashboard'
import KitchenDashboard from './pages/KitchenDashboard'
import HostDashboard from './pages/HostDashboard'
import CashierDashboard from './pages/CashierDashboard'

/**
 * Returns the default dashboard path for the current user's role.
 * Used for post-login redirect and catch-all navigation.
 */
function getDefaultStaffPath() {
  const role = getUserRole()
  if (role === 'admin') return '/admin'
  if (role === 'chef' || role === 'inventory') return '/kitchen'
  if (role === 'waiter') return '/staff'
  if (role === 'receptionist') return '/staff'
  if (role === 'cashier') return '/staff'
  if (role === 'manager') return '/staff'
  if (role === 'customer') return '/customer/account'
  return '/staff'
}

/**
 * Renders the correct dashboard component for the authenticated staff role.
 */
function StaffHome() {
  const role = getUserRole()
  if (role === 'waiter') return <WaiterDashboard />
  if (role === 'chef' || role === 'inventory') return <KitchenDashboard />
  if (role === 'receptionist') return <HostDashboard />
  if (role === 'cashier') return <CashierDashboard />
  return <StaffDashboard />  // fallback for manager + generic staff
}

/**
 * True if the current user has kitchen-only access (inventory / chef without admin access)
 */
function isKitchenOnly() {
  const role = getUserRole()
  return role === 'inventory' || role === 'chef'
}

/**
 * True if the current user is waiter-only (not admin/manager)
 */
function isWaiterOnly() {
  return getUserRole() === 'waiter'
}

/**
 * True if the current user is host/receptionist only
 */
function isHostOnly() {
  return getUserRole() === 'receptionist'
}

function AppRoutes() {
  // Track token in React state so route guards re-evaluate whenever auth changes.
  // getUserRole() reads from localStorage synchronously; pairing it with a state
  // variable that updates on every storage write guarantees the route guards always
  // see the correct role on the render that follows a login/logout.
  const location = useLocation()
  const [_authToken, setAuthToken] = useState(() => localStorage.getItem('token'))

  useEffect(() => {
    // Sync state with localStorage whenever the location changes (i.e. after navigate()).
    setAuthToken(localStorage.getItem('token'))
  }, [location])

  const staffView = isStaffUser()
  const role = getUserRole()

  return (
    <div className={`app-shell ${staffView ? 'staff-shell' : 'customer-shell'}`}>
      <NavBar />
      <Routes>
        {/* Public */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/staff/select" element={<StaffRoleSelect />} />

        {/* Customer routes */}
        <Route path="/customer" element={<CustomerHome />} />
        <Route path="/customer/menu" element={<MenuSearch />} />
        <Route path="/customer/reservation" element={<ReservationForm />} />
        <Route path="/customer/waitlist" element={<WaitlistDashboard readOnly />} />
        <Route
          path="/customer/account"
          element={isCustomerUser() ? <CustomerAccount /> : <Navigate to="/login" replace />}
        />

        {/* Staff home — routes to role-specific dashboard */}
        <Route
          path="/staff"
          element={staffView ? <StaffHome /> : <Navigate to="/login?role=staff" replace />}
        />

        {/* Admin-only routes */}
        <Route
          path="/admin"
          element={isAdminUser() ? <AdminDashboard /> : <Navigate to="/staff" replace />}
        />
        <Route
          path="/staff/manage"
          element={isAdminUser() ? <StaffManagement /> : <Navigate to="/staff" replace />}
        />

        {/* Kitchen route — kitchen staff, chef, admin, manager only */}
        <Route
          path="/kitchen"
          element={
            isKitchenUser() || isAdminUser() || role === 'manager'
              ? <KitchenDashboard />
              : staffView
              ? <Navigate to="/staff" replace />
              : <Navigate to="/customer" replace />
          }
        />

        {/* Waitlist — floor staff, admin, manager can manage; kitchen-only gets redirected */}
        <Route
          path="/waitlist"
          element={
            staffView
              ? isKitchenOnly()
                ? <Navigate to="/kitchen" replace />
                : <WaitlistDashboard />
              : <Navigate to="/customer/waitlist" replace />
          }
        />

        {/* Tables — not for kitchen-only staff */}
        <Route
          path="/tables"
          element={
            staffView
              ? isKitchenOnly()
                ? <Navigate to="/kitchen" replace />
                : <TableMap />
              : <Navigate to="/customer" replace />
          }
        />

        {/* Menu — readable by all; full management only for admin/manager (enforced in backend) */}
        <Route path="/menu" element={<MenuSearch />} />

        {/* Reservations — floor roles + admin/manager; not kitchen-only or waiter */}
        <Route
          path="/reservation"
          element={
            staffView
              ? isKitchenOnly() || isWaiterUser()
                ? <Navigate to="/staff" replace />
                : <ReservationForm />
              : <Navigate to="/customer/reservation" replace />
          }
        />

        {/* Order history — all staff except kitchen-only */}
        <Route
          path="/history"
          element={
            staffView
              ? isKitchenOnly()
                ? <Navigate to="/kitchen" replace />
                : <OrderHistory />
              : <Navigate to="/customer" replace />
          }
        />

        {/* Catch-all */}
        <Route
          path="*"
          element={<Navigate to={staffView ? getDefaultStaffPath() : '/customer'} replace />}
        />
      </Routes>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
