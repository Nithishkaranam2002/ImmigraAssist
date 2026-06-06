import { NavLink, useNavigate } from "react-router-dom"
import {
  MessageSquare,
  FileText,
  Users,
  BarChart3,
  LogOut,
  LayoutDashboard,
  X,
  Briefcase,
  BookOpen,
  ClipboardCheck,
  Bell,
  LineChart,
} from "lucide-react"
import { useAuthStore } from "@/store/authStore"
import { Logo } from "@/components/brand/Logo"
import { cn } from "@/lib/utils"
import type { UserRole } from "@/types"
import {
  canEvalDashboard,
  canPolicyAlerts,
  canReviewQueue,
} from "@/lib/features"

const navItems: {
  to: string
  icon: typeof MessageSquare
  label: string
  minRole: UserRole
  check?: (role: UserRole | undefined) => boolean
}[] = [
  { to: "/chat", icon: MessageSquare, label: "Research Chat", minRole: "junior_associate" },
  { to: "/matters", icon: Briefcase, label: "Matters", minRole: "junior_associate" },
  { to: "/research", icon: BookOpen, label: "Visa Hubs", minRole: "junior_associate" },
  { to: "/reviews", icon: ClipboardCheck, label: "Review Queue", minRole: "attorney", check: canReviewQueue },
  { to: "/documents", icon: FileText, label: "Documents", minRole: "admin" },
  { to: "/users", icon: Users, label: "Team", minRole: "admin" },
  { to: "/admin", icon: LayoutDashboard, label: "Dashboard", minRole: "admin" },
  { to: "/eval", icon: LineChart, label: "Eval Metrics", minRole: "admin", check: canEvalDashboard },
  { to: "/alerts", icon: Bell, label: "Policy Alerts", minRole: "admin", check: canPolicyAlerts },
  { to: "/audit", icon: BarChart3, label: "Audit Logs", minRole: "admin" },
]

interface SidebarProps {
  open?: boolean
  onClose?: () => void
}

export function Sidebar({ open = false, onClose }: SidebarProps) {
  const { user, logout, hasRole } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate("/login")
  }

  const handleNavClick = () => {
    onClose?.()
  }

  const roleLabel = user?.role?.replace(/_/g, " ") ?? ""

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-50 flex flex-col w-72 bg-sidebar text-white transition-transform duration-200 ease-out lg:static lg:translate-x-0 lg:shrink-0",
        open ? "translate-x-0" : "-translate-x-full"
      )}
    >
      <div className="flex items-center justify-between px-5 py-5 border-b border-white/10">
        <Logo size="md" variant="light" />
        <button
          type="button"
          onClick={onClose}
          className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
          aria-label="Close menu"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <nav className="flex-1 px-3 py-5 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          if (!hasRole(item.minRole)) return null
          if (item.check && !item.check(user?.role)) return null
          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={handleNavClick}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                  isActive
                    ? "bg-brand-600 text-white shadow-lg shadow-brand-600/30"
                    : "text-slate-400 hover:bg-white/5 hover:text-white"
                )
              }
            >
              <item.icon className="w-4 h-4 shrink-0" />
              {item.label}
            </NavLink>
          )
        })}
      </nav>

      <div className="px-3 py-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-3 py-2.5 mb-2 rounded-lg bg-white/5">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-sm font-bold shrink-0">
            {user?.full_name?.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.full_name}</p>
            <p className="text-xs text-slate-400 capitalize">{roleLabel}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm text-slate-400 hover:bg-white/5 hover:text-white transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </aside>
  )
}
