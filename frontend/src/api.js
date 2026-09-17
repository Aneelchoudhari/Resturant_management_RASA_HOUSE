/* All API calls go through /api (proxied to http://localhost:8000 by Vite) */
const BASE = '/api'

const getToken = () => localStorage.getItem('token')

const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${getToken()}`,
})

const json = (res) => {
  if (!res.ok) return res.json().then((e) => Promise.reject(e.detail || 'Request failed'))
  if (res.status === 204) return null
  return res.json()
}

/* ── Auth ──────────────────────────────────────────────────────────────────── */
export const login = (email, password) => {
  const body = new URLSearchParams({ username: email, password })
  return fetch(`${BASE}/auth/login`, { method: 'POST', body }).then(json)
}

export const register = (data) =>
  fetch(`${BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(json)

/* ── Waitlist ──────────────────────────────────────────────────────────────── */
export const fetchWaitlist = () => fetch(`${BASE}/waitlist/`).then(json)

export const joinWaitlist = (data) =>
  fetch(`${BASE}/waitlist/join`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(json)

/* ── Tables ────────────────────────────────────────────────────────────────── */
export const fetchTables = () => fetch(`${BASE}/tables/`).then(json)

export const fetchAllocation = () => fetch(`${BASE}/tables/allocate`).then(json)

export const fetchCombine = (partySize) =>
  fetch(`${BASE}/tables/combine?party_size=${partySize}`).then(json)

/* ── Menu ──────────────────────────────────────────────────────────────────── */
export const fetchMenu = () => fetch(`${BASE}/menu/`).then(json)

export const searchMenu = (q) =>
  fetch(`${BASE}/menu/search${q ? `?q=${encodeURIComponent(q)}` : ''}`).then(json)

export const fetchMenuByCategory = (tag) =>
  fetch(`${BASE}/menu/category/${encodeURIComponent(tag)}`).then(json)

/* ── Reservations ──────────────────────────────────────────────────────────── */
export const createReservation = (data) =>
  fetch(`${BASE}/reservations/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(json)

/* ── Orders ────────────────────────────────────────────────────────────────── */
export const createOrder = (data) =>
  fetch(`${BASE}/orders/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  }).then(json)

export const fetchOrderHistory = (from, to) => {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  return fetch(`${BASE}/orders/history?${params}`).then(json)
}

/* ── Kitchen ───────────────────────────────────────────────────────────────── */
export const fetchKitchenQueue = (station) =>
  fetch(`${BASE}/kitchen/${station}`).then(json)
