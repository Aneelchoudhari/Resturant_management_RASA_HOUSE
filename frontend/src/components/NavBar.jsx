import { NavLink, useNavigate } from 'react-router-dom'

export default function NavBar() {
  const navigate = useNavigate()
  const isLoggedIn = !!localStorage.getItem('token')

  const logout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }

  return (
    <nav>
      <span className="brand">🍽 RestaurantMS</span>
      <NavLink to="/waitlist">Waitlist</NavLink>
      <NavLink to="/tables">Tables</NavLink>
      <NavLink to="/menu">Menu</NavLink>
      <NavLink to="/reservation">Reservation</NavLink>
      <NavLink to="/kitchen">Kitchen</NavLink>
      <NavLink to="/history">History</NavLink>
      {isLoggedIn ? (
        <button className="logout" onClick={logout}>Logout</button>
      ) : (
        <NavLink to="/login">Login</NavLink>
      )}
    </nav>
  )
}
