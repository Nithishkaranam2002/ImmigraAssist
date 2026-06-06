import { useState } from "react"
import { useNavigate, Navigate, Link } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { AuthLayout } from "@/components/auth/AuthLayout"
import { authService } from "@/services/authService"
import { useAuthStore } from "@/store/authStore"
import { getApiErrorMessage } from "@/lib/utils"

const loginSchema = z.object({
  email: z.string().email("Invalid email"),
  password: z.string().min(1, "Password required"),
})

type LoginForm = z.infer<typeof loginSchema>

export function LoginPage() {
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { setAuth, isAuthenticated } = useAuthStore()

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  if (isAuthenticated) return <Navigate to="/chat" replace />

  const onSubmit = async (data: LoginForm) => {
    setLoading(true)
    setError("")
    try {
      const response = await authService.login(data)
      setAuth(response.access_token, {
        id: response.user_id,
        full_name: response.full_name,
        email: data.email,
        role: response.role,
        is_active: true,
        created_at: new Date().toISOString(),
      })
      navigate("/chat")
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Login failed"))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to access your legal research workspace"
    >
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Email</label>
            <Input type="email" placeholder="you@firm.com" {...register("email")} />
            {errors.email && (
              <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Password</label>
            <Input type="password" placeholder="••••••••" {...register("password")} />
            {errors.password && (
              <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>
            )}
          </div>

          {error && (
            <div className="text-red-600 text-sm text-center bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <Button type="submit" className="w-full h-11" disabled={loading}>
            {loading ? (
              <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Signing in...</>
            ) : (
              "Sign In"
            )}
          </Button>

          <p className="text-center text-sm text-slate-500">
            Don't have an account?{" "}
            <Link to="/signup" className="text-brand-600 hover:text-brand-700 font-medium">
              Create one
            </Link>
          </p>
        </form>
      </div>
    </AuthLayout>
  )
}
