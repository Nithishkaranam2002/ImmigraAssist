import { NavLink, useNavigate } from "react-router-dom"
import { MessageSquare, FileText, Users, BarChart3, LogOut, Scale, LayoutDashboard } from "lucide-react"
import { useAuthStore } from "@/store/authStore"
import { cn } from "@/lib/utils"

const navItems = [
  { to: "/chat", icon: MessageSquare, label: "Chat", minRole: "junior_associate" },
  { to: "/documents", icon: FileText, label: "Documents", minRole: "admin" },
  { to: "/users", icon: Users, label: "Users", minRole: "admin" },
  { to: "/admin", icon: LayoutDashboard, label: "Dashboard", minRole: "admin" },
  { to: "/audit", icon: BarChart3, label: "Audit Logs", minRole: "admin" },
]

export function Sidebar() {
  const { user, logout, hasRole } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate("/login")
  }

  return (
    <div className="flex flex-col h-full w-64 bg-gray-900 text-white">
      <div className="flex items-center gap-3 px-6 py-5 border-b border-gray-700">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <Scale className="w-4 h-4 text-white" />
        </div>
        <div>
          <h1 className="font-bold text-sm">ImmigraAssist</h1>
          <p className="text-xs text-gray-400">From Policies to Precedents</p>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          if (!hasRole(item.minRole as any)) return null
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                )
              }
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </NavLink>
          )
        })}
      </nav>

      <div className="px-3 py-4 border-t border-gray-700">
        <div className="flex items-center gap-3 px-3 py-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold">
            {user?.full_name?.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.full_name}</p>
            <p className="text-xs text-gray-400 capitalize">{user?.role?.replace("_", " ")}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </div>
  )
}
