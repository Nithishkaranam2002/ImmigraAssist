import { lazy, Suspense } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { Toaster } from "@/components/ui/toaster"
import { AppLayout } from "@/components/layout/AppLayout"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { LandingPage } from "@/pages/LandingPage"
import { LoginPage } from "@/pages/LoginPage"
import { SignupPage } from "@/pages/SignupPage"
import { ChatPage } from "@/pages/ChatPage"
import { AdminPage } from "@/pages/AdminPage"
import { DocumentsPage } from "@/pages/DocumentsPage"
import { AuditPage } from "@/pages/AuditPage"
import { UsersPage } from "@/pages/UsersPage"
import { MattersPage } from "@/pages/MattersPage"
import { MatterDetailPage } from "@/pages/MatterDetailPage"
import { ResearchHubPage } from "@/pages/ResearchHubPage"
import { ResearchVisaPage } from "@/pages/ResearchVisaPage"
import { ReviewQueuePage } from "@/pages/ReviewQueuePage"
import { Loader2 } from "lucide-react"

const EvalDashboardPage = lazy(() =>
  import("@/pages/EvalDashboardPage").then((m) => ({ default: m.EvalDashboardPage }))
)
import { AlertsPage } from "@/pages/AlertsPage"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30000,
    },
  },
})

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route element={<AppLayout />}>
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/matters" element={<MattersPage />} />
              <Route path="/matters/:matterId" element={<MatterDetailPage />} />
              <Route path="/research" element={<ResearchHubPage />} />
              <Route path="/research/:visaType" element={<ResearchVisaPage />} />
              <Route element={<ProtectedRoute minRole="attorney" />}>
                <Route path="/reviews" element={<ReviewQueuePage />} />
              </Route>
              <Route element={<ProtectedRoute minRole="admin" />}>
                <Route path="/documents" element={<DocumentsPage />} />
                <Route path="/admin" element={<AdminPage />} />
                <Route path="/users" element={<UsersPage />} />
                <Route path="/audit" element={<AuditPage />} />
                <Route
                  path="/eval"
                  element={
                    <Suspense
                      fallback={
                        <div className="h-full flex items-center justify-center">
                          <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
                        </div>
                      }
                    >
                      <EvalDashboardPage />
                    </Suspense>
                  }
                />
                <Route path="/alerts" element={<AlertsPage />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <Toaster />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
