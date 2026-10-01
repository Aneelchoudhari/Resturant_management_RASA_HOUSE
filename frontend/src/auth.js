export const getToken = () => localStorage.getItem('token') || ''

export const getUserRole = () => {
  const token = getToken()
  if (!token) return 'guest'

  const payload = token.split('.')[1]
  if (!payload) return 'guest'

  try {
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=')
    const binary = atob(padded)
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0))
    const decoded = JSON.parse(new TextDecoder().decode(bytes))
    return decoded.role || 'guest'
  } catch {
    return 'guest'
  }
}

const STAFF_ROLES = ['staff', 'admin', 'manager', 'waiter', 'chef', 'cashier', 'inventory', 'receptionist']
const KITCHEN_ROLES = ['chef', 'inventory']
const FLOOR_ROLES = ['waiter', 'receptionist', 'admin', 'manager']
const HOST_ROLES = ['receptionist', 'admin', 'manager']

export const isStaffUser = () => STAFF_ROLES.includes(getUserRole())
export const isCustomerUser = () => getUserRole() === 'customer'
export const isAdminUser = () => getUserRole() === 'admin'
export const isManagerUser = () => ['admin', 'manager'].includes(getUserRole())
export const isWaiterUser = () => getUserRole() === 'waiter'
export const isKitchenUser = () => KITCHEN_ROLES.includes(getUserRole())
export const isHostUser = () => HOST_ROLES.includes(getUserRole())
export const isCashierUser = () => ['cashier', 'admin', 'manager', 'waiter'].includes(getUserRole())

/** Returns a human-readable label for the current role */
export const getRoleLabel = () => {
  const map = {
    admin: 'Admin',
    manager: 'Manager',
    waiter: 'Waiter',
    chef: 'Chef',
    cashier: 'Cashier',
    receptionist: 'Host',
    inventory: 'Kitchen Staff',
    staff: 'Staff',
    customer: 'Customer',
    guest: 'Guest',
  }
  return map[getUserRole()] || 'Staff'
}
