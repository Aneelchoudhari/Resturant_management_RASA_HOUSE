import { Link } from 'react-router-dom'

const highlights = [
  {
    title: 'Tandoor & flame',
    text: 'Clay-oven cooking, bright chutneys, and the kind of aroma that reaches the table first.',
    image: 'https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=900&q=85',
  },
  {
    title: 'East meets west',
    text: 'Comforting Indian flavours meet familiar western favourites in a room made for everyone.',
    image: 'https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=900&q=85',
  },
  {
    title: 'Fresh perspective',
    text: 'Seasonal produce, hand-ground spices, and modern plates with a little something unexpected.',
    image: 'https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=900&q=85',
  },
]

const dishes = [
  { name: 'Tandoori Chicken', detail: 'Yoghurt, Kashmiri chilli, lemon, coriander', price: '₹420' },
  { name: 'Masala Cream Pasta', detail: 'Roasted tomato, curry leaf, parmesan', price: '₹390' },
  { name: 'Gulab Jamun Cheesecake', detail: 'Saffron cream, pistachio, biscuit crumb', price: '₹220' },
]

export default function LandingPage() {
  return (
    <main className="landing-page">
      <header className="landing-nav">
        <Link className="landing-brand" to="/">RASA<span>HOUSE</span></Link>
        <nav className="landing-links" aria-label="Main navigation">
          <a href="#story">Our story</a>
          <a href="#menu">Menu</a>
          <a href="#visit">Visit</a>
        </nav>
        <Link className="landing-nav-cta" to="/customer">Dine with us <span>↗</span></Link>
      </header>

      <section className="landing-hero">
        <div className="hero-copy">
          <p className="eyebrow">Indian + western kitchen · Est. 2018</p>
          <h1>Spice, soul.<br /><em>Good company.</em></h1>
          <p className="hero-lede">Indian soul, western ease, and a table waiting for you in the heart of the neighbourhood.</p>
          <div className="hero-actions">
            <Link className="landing-primary" to="/customer/menu">Explore the menu <span>↗</span></Link>
            <Link className="landing-text-link" to="/customer/reservation">Reserve a table <span>→</span></Link>
          </div>
        </div>
        <div className="hero-image-wrap">
          <img src="https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1500&q=88" alt="Warm restaurant interior with tables and ambient lighting" />
          <div className="hero-image-note"><span>Open today</span><strong>12:00 — 23:00</strong></div>
        </div>
        <div className="hero-scroll">Scroll to savour <span>↓</span></div>
      </section>

      <section className="welcome-strip" id="story">
        <p className="eyebrow">From our rasoi</p>
        <div>
          <h2>Old recipes, new energy,<br /><em>hospitality without the fuss.</em></h2>
          <p>We bring Indian warmth to western comfort food and western simplicity to Indian classics. Come for the tandoor, stay for the easy conversation and the last sip of chai.</p>
        </div>
      </section>

      <section className="highlight-grid">
        {highlights.map((highlight, index) => (
          <article className={`highlight-card highlight-${index + 1}`} key={highlight.title}>
            <img src={highlight.image} alt="" />
            <div><span>0{index + 1}</span><h3>{highlight.title}</h3><p>{highlight.text}</p></div>
          </article>
        ))}
      </section>

      <section className="menu-preview" id="menu">
        <div className="section-heading"><div><p className="eyebrow">From the kitchen</p><h2>Today’s <em>favourites</em></h2></div><Link className="landing-text-link" to="/customer/menu">See full menu <span>↗</span></Link></div>
        <div className="dish-list">
          {dishes.map((dish) => <div className="dish-row" key={dish.name}><div><h3>{dish.name}</h3><p>{dish.detail}</p></div><strong>{dish.price}</strong></div>)}
        </div>
      </section>

      <section className="choose-path" id="visit">
        <div><p className="eyebrow">Your table is ready</p><h2>How would you like<br /><em>to continue?</em></h2></div>
        <div className="path-cards">
          <Link className="path-card path-customer" to="/customer"><span className="path-number">01</span><span><strong>Customer</strong><small>Browse, order, reserve</small></span><b>↗</b></Link>
          <Link className="path-card path-staff" to="/staff/select"><span className="path-number">02</span><span><strong>Staff</strong><small>Choose your workspace</small></span><b>↗</b></Link>
        </div>
      </section>

      <footer className="landing-footer"><strong>RASA<span>HOUSE</span></strong><span>14 Orchard Lane, Downtown</span><span>hello@rasahouse.restaurant</span><span>Tue — Sun · 12:00 — 23:00</span></footer>
    </main>
  )
}
