import { useState, useEffect } from "react"
import { useNavigate, Navigate, Link, useSearchParams } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Loader2, CheckCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { AuthLayout } from "@/components/auth/AuthLayout"
import { authService } from "@/services/authService"
import { useAuthStore } from "@/store/authStore"
import api from "@/services/api"

const signupSchema = z.object({
  full_name: z.string().min(2, "Full name must be at least 2 characters"),
  email: z.string().email("Invalid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  confirm_password: z.string(),
  designation: z.string().optional(),
}).refine((data) => data.password === data.confirm_password, {
  message: "Passwords do not match",
  path: ["confirm_password"],
})

type SignupForm = z.infer<typeof signupSchema>

interface InviteInfo {
  valid: boolean
  role: string
  designation: string | null
  email: string | null
}

export function SignupPage() {
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [inviteInfo, setInviteInfo] = useState<InviteInfo | null>(null)
  const [inviteLoading, setInviteLoading] = useState(false)
  const [searchParams] = useSearchParams()
  const inviteToken = searchParams.get("token")
  const navigate = useNavigate()
  const { setAuth, isAuthenticated } = useAuthStore()

  const { register, handleSubmit, setValue, formState: { errors } } = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
  })

  useEffect(() => {
    if (inviteToken) {
      setInviteLoading(true)
      api.get(`/invites/validate/${inviteToken}`)
        .then((res) => {
          setInviteInfo(res.data)
          if (res.data.email) setValue("email", res.data.email)
          if (res.data.designation) setValue("designation", res.data.designation)
        })
        .catch(() => setError("This invite link is invalid or has expired."))
        .finally(() => setInviteLoading(false))
    }
  }, [inviteToken, setValue])

  if (isAuthenticated) return <Navigate to="/chat" replace />

  const onSubmit = async (data: SignupForm) => {
    setLoading(true)
    setError("")
    try {
      const response = await authService.register({
        full_name: data.full_name,
        email: data.email,
        password: data.password,
        role: "junior_associate",
        designation: data.designation,
        invite_token: inviteToken || undefined,
      })
      setAuth(response.access_token, {
        id: response.user_id,
        full_name: response.full_name,
        email: data.email,
        role: response.role,
        is_active: true,
        created_at: new Date().toISOString(),
      })
      navigate("/chat")
    } catch (err: any) {
      setError(err.response?.data?.detail || "Signup failed. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Join your firm's immigration research workspace"
    >
      {inviteToken && inviteInfo && (
        <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-lg px-4 py-3 mb-4">
          <CheckCircle className="w-4 h-4 text-green-600 shrink-0" />
          <div>
            <p className="text-sm font-medium text-green-800">Valid invite link</p>
            <p className="text-xs text-green-600">
              You'll be registered as {inviteInfo.role.replace("_", " ")}
              {inviteInfo.designation ? ` — ${inviteInfo.designation}` : ""}
            </p>
          </div>
        </div>
      )}

      {inviteLoading && (
        <div className="flex items-center justify-center gap-2 mb-4 text-slate-500 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          Validating invite...
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Full Name</label>
            <Input type="text" placeholder="John Smith" {...register("full_name")} />
            {errors.full_name && <p className="text-red-500 text-xs mt-1">{errors.full_name.message}</p>}
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Email</label>
            <Input
              type="email"
              placeholder="you@firm.com"
              {...register("email")}
              readOnly={!!inviteInfo?.email}
              className={inviteInfo?.email ? "bg-slate-50" : ""}
            />
            {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Designation</label>
            <Input
              type="text"
              placeholder="e.g. Junior Immigration Associate"
              {...register("designation")}
              readOnly={!!inviteInfo?.designation}
              className={inviteInfo?.designation ? "bg-slate-50" : ""}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Password</label>
            <Input type="password" placeholder="Min 8 characters" {...register("password")} />
            {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Confirm Password</label>
            <Input type="password" placeholder="Repeat your password" {...register("confirm_password")} />
            {errors.confirm_password && <p className="text-red-500 text-xs mt-1">{errors.confirm_password.message}</p>}
          </div>

          {error && (
            <div className="text-red-600 text-sm text-center bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <Button type="submit" className="w-full h-11" disabled={loading}>
            {loading ? (
              <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Creating account...</>
            ) : (
              "Create Account"
            )}
          </Button>

          <p className="text-center text-sm text-slate-500">
            Already have an account?{" "}
            <Link to="/login" className="text-brand-600 hover:text-brand-700 font-medium">Sign in</Link>
          </p>
        </form>
      </div>

      {!inviteToken && (
        <p className="text-center text-xs text-slate-400 mt-4">
          New accounts start as Junior Associate. Contact your admin to update your role.
        </p>
      )}
    </AuthLayout>
  )
}
