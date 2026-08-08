import { create } from "zustand"
import type { User, UserRole } from "@/types"
import { resetClientState } from "@/lib/resetClientState"

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  setAuth: (token: string, user: User) => void
  logout: () => void
  hasRole: (role: UserRole) => boolean
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: (() => {
    try {
      const stored = localStorage.getItem("user")
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })(),
  token: localStorage.getItem("access_token"),
  isAuthenticated: !!localStorage.getItem("access_token"),

  setAuth: (token, user) => {
    // Drop any prior user's in-memory chat/query cache before activating
    // the new session (SPA login does not reload the page).
    resetClientState()
    localStorage.setItem("access_token", token)
    localStorage.setItem("user", JSON.stringify(user))
    set({ token, user, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem("access_token")
    localStorage.removeItem("user")
    set({ token: null, user: null, isAuthenticated: false })
    resetClientState()
  },

  hasRole: (role) => {
    const roleHierarchy: Record<UserRole, number> = {
      super_admin: 4,
      admin: 3,
      attorney: 2,
      junior_associate: 1,
    }
    const userRole = get().user?.role
    if (!userRole) return false
    return roleHierarchy[userRole] >= roleHierarchy[role]
  },
}))
