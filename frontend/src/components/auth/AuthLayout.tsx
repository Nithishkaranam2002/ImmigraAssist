import type { ReactNode } from "react"
import { BookOpen, Gavel, Shield } from "lucide-react"
import { Logo } from "@/components/brand/Logo"

interface AuthLayoutProps {
  children: ReactNode
  title: string
  subtitle: string
}

const features = [
  { icon: BookOpen, label: "USCIS Policy Manual", desc: "657+ policy sections indexed" },
  { icon: Gavel, label: "BIA & Court Cases", desc: "5,800+ precedents searchable" },
  { icon: Shield, label: "Cited Answers", desc: "Every response backed by sources" },
]

export function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex">
      <div className="hidden lg:flex lg:w-[45%] xl:w-[42%] gradient-hero flex-col justify-between p-10 xl:p-14 text-white relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 -left-10 w-72 h-72 rounded-full bg-white blur-3xl" />
          <div className="absolute bottom-10 right-0 w-96 h-96 rounded-full bg-brand-500 blur-3xl" />
        </div>

        <div className="relative z-10">
          <Logo size="lg" variant="light" />
        </div>

        <div className="relative z-10 space-y-8">
          <div>
            <h2 className="font-serif text-3xl xl:text-4xl font-semibold leading-tight">
              Immigration legal research,<br />answered in seconds.
            </h2>
            <p className="mt-4 text-slate-300 text-sm leading-relaxed max-w-md">
              RAG-powered assistant for immigration attorneys. Query USCIS policies,
              BIA decisions, and CourtListener cases with cited, audit-ready answers.
            </p>
          </div>

          <div className="space-y-4">
            {features.map((f) => (
              <div key={f.label} className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-white/10 flex items-center justify-center shrink-0">
                  <f.icon className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-sm font-medium">{f.label}</p>
                  <p className="text-xs text-slate-400">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative z-10 text-xs text-slate-500">
          Built for immigration law firms · Not legal advice
        </p>
      </div>

      <div className="flex-1 flex flex-col justify-center px-6 py-10 sm:px-10 bg-surface">
        <div className="lg:hidden mb-8 flex justify-center">
          <Logo size="md" />
        </div>

        <div className="w-full max-w-md mx-auto animate-slide-up">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{title}</h1>
            <p className="text-sm text-slate-500 mt-1">{subtitle}</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}
