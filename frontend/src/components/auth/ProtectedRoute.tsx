import { Navigate, Outlet } from "react-router-dom"
import { useAuthStore } from "@/store/authStore"
import type { UserRole } from "@/types"

interface ProtectedRouteProps {
  minRole?: UserRole
}

export function ProtectedRoute({ minRole }: ProtectedRouteProps) {
  const { isAuthenticated, hasRole } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (minRole && !hasRole(minRole)) {
    return <Navigate to="/chat" replace />
  }

  return <Outlet />
}
