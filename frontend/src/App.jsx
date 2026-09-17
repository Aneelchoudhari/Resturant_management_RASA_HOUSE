import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import NavBar from './components/NavBar'
import Login from './pages/Login'
import WaitlistDashboard from './pages/WaitlistDashboard'
import TableMap from './pages/TableMap'
import MenuSearch from './pages/MenuSearch'
import ReservationForm from './pages/ReservationForm'
import KitchenView from './pages/KitchenView'
import OrderHistory from './pages/OrderHistory'

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<Navigate to="/waitlist" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/waitlist" element={<WaitlistDashboard />} />
        <Route path="/tables" element={<TableMap />} />
        <Route path="/menu" element={<MenuSearch />} />
        <Route path="/reservation" element={<ReservationForm />} />
        <Route path="/kitchen" element={<KitchenView />} />
        <Route path="/history" element={<OrderHistory />} />
      </Routes>
    </BrowserRouter>
  )
}
