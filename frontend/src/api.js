/* All API calls go through /api (proxied to http://localhost:8000 by Vite) */
const BASE = '/api'

const getToken = () => localStorage.getItem('token')

const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${getToken()}`,
})

const optionalAuthHeaders = () => {
  const token = getToken()
  return token
    ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
    : { 'Content-Type': 'application/json' }
}

const json = async (res) => {
  if (res.status === 204) return null

  const text = await res.text()
  let payload = null
  try {
    payload = text ? JSON.parse(text) : null
  } catch {
    throw new Error(`Request failed (${res.status}): server returned invalid JSON`)
  }

  if (!res.ok) {
    throw new Error(payload?.detail || `Request failed (${res.status})`)
  }
  return payload
}

/* ── Auth ──────────────────────────────────────────────────────────────────── */
export const login = (email, password) => {
  const body = new URLSearchParams({ username: email, password })
  return fetch(`${BASE}/auth/login`, { method: 'POST', body }).then(json)
}

export const fetchStaff = () =>
  fetch(`${BASE}/staff/`, { headers: authHeaders() }).then(json)

export const fetchReservations = () =>
  fetch(`${BASE}/reservations/`, { headers: authHeaders() }).then(json)

export const fetchOrders = () =>
  fetch(`${BASE}/orders/history`, { headers: authHeaders() }).then(json)

export const fetchMenuItems = () =>
  fetch(`${BASE}/menu/`).then(json)

export const createStaff = (data) =>
  fetch(`${BASE}/staff/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  }).then(json)

export const updateStaff = (id, data) =>
  fetch(`${BASE}/staff/${id}`, { method: 'PUT', headers: authHeaders(), body: JSON.stringify(data) }).then(json)

export const deleteStaff = (id) =>
  fetch(`${BASE}/staff/${id}`, { method: 'DELETE', headers: authHeaders() }).then(json)

export const fetchAdminCustomers = () =>
  fetch(`${BASE}/admin/customers`, { headers: authHeaders() }).then(json)

export const fetchAdminAudit = () =>
  fetch(`${BASE}/admin/audit`, { headers: authHeaders() }).then(json)

export const fetchAdminReports = () =>
  fetch(`${BASE}/admin/reports`, { headers: authHeaders() }).then(json)

export const fetchAdminSummary = () =>
  fetch(`${BASE}/admin/summary`, { headers: authHeaders() }).then(json)

export const customerLogin = (email, password) => {
  const body = new URLSearchParams({ username: email, password })
  return fetch(`${BASE}/auth/customer/login`, { method: 'POST', body }).then(json)
}

export const registerCustomer = (data) =>
  fetch(`${BASE}/auth/customer/register`, {
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

// Staff-only: add VIP or Reservation entry (awards loyalty points)
export const staffJoinWaitlist = (data) =>
  fetch(`${BASE}/waitlist/staff-join`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  }).then(json)

/* ── Tables ────────────────────────────────────────────────────────────────── */
export const fetchTables = () => fetch(`${BASE}/tables/`).then(json)

// Auth required for operational table queries
export const fetchAllocation = () =>
  fetch(`${BASE}/tables/allocate`, { headers: authHeaders() }).then(json)

export const fetchCombine = (partySize) =>
  fetch(`${BASE}/tables/combine?party_size=${partySize}`, { headers: authHeaders() }).then(json)

// Admin/manager: create or delete a table
export const createTable = (data) =>
  fetch(`${BASE}/tables/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  }).then(json)

// Admin: create table via admin endpoint (with audit log)
export const adminCreateTable = (data) =>
  fetch(`${BASE}/admin/tables`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  }).then(json)

// Admin: master allocate a table to any customer
export const adminAllocateTable = (data) =>
  fetch(`${BASE}/admin/tables/allocate`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  }).then(json)

export const updateTable = (id, data) =>
  fetch(`${BASE}/tables/${id}`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(data),
  }).then(json)

export const deleteTable = (id) =>
  fetch(`${BASE}/tables/${id}`, { method: 'DELETE', headers: authHeaders() }).then(json)

// Waiter/host: update only table status
export const updateTableStatus = (id, status) =>
  fetch(`${BASE}/tables/${id}/status`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify({ status }),
  }).then(json)

/* ── Menu ──────────────────────────────────────────────────────────────────── */
export const fetchMenu = () => fetch(`${BASE}/menu/`).then(json)

export const searchMenu = (q) =>
  fetch(`${BASE}/menu/search${q ? `?q=${encodeURIComponent(q)}` : ''}`).then(json)

export const fetchMenuByCategory = (tag) =>
  fetch(`${BASE}/menu/category/${encodeURIComponent(tag)}`).then(json)

// Admin/manager: create, update, delete menu items
export const createMenuItem = (data) =>
  fetch(`${BASE}/menu/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  }).then(json)

export const updateMenuItem = (id, data) =>
  fetch(`${BASE}/menu/${id}`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(data),
  }).then(json)

export const deleteMenuItem = (id) =>
  fetch(`${BASE}/menu/${id}`, { method: 'DELETE', headers: authHeaders() }).then(json)

export const toggleMenuItemAvailability = (id) =>
  fetch(`${BASE}/menu/${id}/availability`, {
    method: 'PATCH',
    headers: authHeaders(),
  }).then(json)

/* ── Reservations ──────────────────────────────────────────────────────────── */
export const createReservation = (data) =>
  fetch(`${BASE}/reservations/`, {
    method: 'POST',
    headers: optionalAuthHeaders(),
    body: JSON.stringify(data),
  }).then(json)

export const updateReservationStatus = (id, data) =>
  fetch(`${BASE}/reservations/${id}/status`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(data),
  }).then(json)

export const fetchCustomerAccount = () =>
  fetch(`${BASE}/reservations/account`, { headers: authHeaders() }).then(json)

export const fetchCustomerReservations = () =>
  fetch(`${BASE}/reservations/mine`, { headers: authHeaders() }).then(json)

export const fetchCustomerOrders = () =>
  fetch(`${BASE}/orders/mine`, { headers: authHeaders() }).then(json)

/* ── Orders ────────────────────────────────────────────────────────────────── */
// Staff (waiter) creates order
export const createOrder = (data) =>
  fetch(`${BASE}/orders/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  }).then(json)

// Customer places order from their cart
export const createCustomerOrder = (data) =>
  fetch(`${BASE}/orders/customer`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  }).then(json)

// Staff: all active orders
export const fetchActiveOrders = () =>
  fetch(`${BASE}/orders/active`, { headers: authHeaders() }).then(json)

// Staff: order history with date filter
export const fetchOrderHistory = (from, to) => {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  return fetch(`${BASE}/orders/history?${params}`, { headers: authHeaders() }).then(json)
}

export const updateOrderStatus = (orderId, status) =>
  fetch(`${BASE}/orders/${orderId}/status`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify({ status }),
  }).then(json)

export const completePayment = (orderId, method) =>
  fetch(`${BASE}/orders/${orderId}/payment`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ method }),
  }).then(json)

/* ── Kitchen ───────────────────────────────────────────────────────────────── */
// Auth required — chef/inventory (kitchen staff) roles
export const fetchKitchenQueue = (station) =>
  fetch(`${BASE}/kitchen/${station}`, { headers: authHeaders() }).then(json)
