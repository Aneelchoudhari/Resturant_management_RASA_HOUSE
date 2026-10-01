import { Link } from 'react-router-dom'
import { isCustomerUser } from '../auth'

const features = [
  {
    emoji: '🍽',
    title: 'Browse our menu',
    description: 'Explore seasonal dishes, view ingredients, prices, and availability. Search by category or name.',
    to: '/customer/menu',
    cta: 'View menu',
  },
  {
    emoji: '📅',
    title: 'Reserve a table',
    description: 'Book your preferred date and time. We confirm your seating and keep you updated.',
    to: '/customer/reservation',
    cta: 'Make a reservation',
  },
  {
    emoji: '🚶',
    title: 'Check the queue',
    description: 'See your position in the live waitlist and get an idea of current wait times.',
    to: '/customer/waitlist',
    cta: 'View waitlist',
  },
]

export default function CustomerHome() {
  const loggedIn = isCustomerUser()

  return (
    <div className="customer-home">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="ch-hero">
        <div className="ch-hero-text">
          <p className="ch-eyebrow">Welcome to RASA HOUSE</p>
          <h1 className="ch-headline">
            Your table is<br /><em>waiting for you.</em>
          </h1>
          <p className="ch-sub">
            Reserve a table, explore our menu, or check your place in the queue — everything you need for a seamless dining experience.
          </p>
          <div className="ch-actions">
            <Link className="btn btn-primary" to="/customer/reservation">Reserve a table</Link>
            <Link className="ch-text-link" to="/customer/menu">Explore the menu →</Link>
          </div>
        </div>
        <div className="ch-hero-info">
          <div className="ch-info-card">
            <span>📍</span>
            <div>
              <strong>Location</strong>
              <p>14 Orchard Lane, Downtown</p>
            </div>
          </div>
          <div className="ch-info-card">
            <span>🕐</span>
            <div>
              <strong>Hours</strong>
              <p>Tue — Sun · 12:00 — 23:00</p>
            </div>
          </div>
          <div className="ch-info-card">
            <span>📞</span>
            <div>
              <strong>Contact</strong>
              <p>hello@rasahouse.restaurant</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Feature cards ─────────────────────────────────────────────────── */}
      <section className="ch-features">
        {features.map(f => (
          <div className="ch-feature-card" key={f.to}>
            <span className="ch-feature-icon">{f.emoji}</span>
            <h2>{f.title}</h2>
            <p>{f.description}</p>
            <Link className="btn btn-primary" to={f.to}>{f.cta}</Link>
          </div>
        ))}
      </section>

      {/* ── Loyalty / account promo ───────────────────────────────────────── */}
      {loggedIn ? (
        <section className="ch-loyalty-strip">
          <span>⭐</span>
          <div>
            <strong>You earn loyalty points with every reservation.</strong>
            <span>VIP bookings earn 20 points · Reservation bookings earn 10 points · Every 100 points = ₹100 off your bill.</span>
          </div>
          <Link className="btn btn-primary" to="/customer/account">My Account →</Link>
        </section>
      ) : (
        <section className="ch-loyalty-strip">
          <span>💎</span>
          <div>
            <strong>Earn loyalty rewards with a free account.</strong>
            <span>Collect points on every reservation. 100 points = ₹100 off your next bill.</span>
          </div>
          <Link className="btn btn-primary" to="/login">Create account →</Link>
        </section>
      )}
    </div>
  )
}
