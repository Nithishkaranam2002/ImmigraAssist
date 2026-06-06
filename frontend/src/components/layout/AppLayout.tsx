import { useState } from "react"
import { Outlet, Navigate } from "react-router-dom"
import { Menu } from "lucide-react"
import { Sidebar } from "./Sidebar"
import { AppFooter } from "./AppFooter"
import { useAuthStore } from "@/store/authStore"
import { Button } from "@/components/ui/button"

export function AppLayout() {
  const { isAuthenticated } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex h-screen bg-surface overflow-hidden">
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex flex-1 flex-col min-w-0">
        <header className="lg:hidden flex items-center gap-3 px-4 py-3 border-b border-slate-200 bg-white shrink-0">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" />
          </Button>
          <span className="font-semibold text-slate-900 text-sm">ImmigraAssist</span>
        </header>

        <main className="flex-1 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-hidden">
            <Outlet />
          </div>
          <AppFooter />
        </main>
      </div>
    </div>
  )
}
