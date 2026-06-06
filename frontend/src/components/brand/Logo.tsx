import { Scale } from "lucide-react"
import { cn } from "@/lib/utils"

interface LogoProps {
  size?: "sm" | "md" | "lg"
  variant?: "light" | "dark"
  showTagline?: boolean
  className?: string
}

const sizes = {
  sm: { icon: "w-7 h-7", iconInner: "w-3.5 h-3.5", title: "text-sm", tag: "text-[10px]" },
  md: { icon: "w-9 h-9", iconInner: "w-4 h-4", title: "text-base", tag: "text-xs" },
  lg: { icon: "w-11 h-11", iconInner: "w-5 h-5", title: "text-xl", tag: "text-sm" },
}

export function Logo({ size = "md", variant = "dark", showTagline = true, className }: LogoProps) {
  const s = sizes[size]
  const isLight = variant === "light"

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className={cn(s.icon, "rounded-xl bg-brand-600 flex items-center justify-center shadow-lg shadow-brand-600/25")}>
        <Scale className={cn(s.iconInner, "text-white")} />
      </div>
      <div>
        <h1 className={cn(s.title, "font-bold tracking-tight", isLight ? "text-white" : "text-slate-900")}>
          ImmigraAssist
        </h1>
        {showTagline && (
          <p className={cn(s.tag, isLight ? "text-slate-300" : "text-slate-500")}>
            From Policies to Precedents
          </p>
        )}
      </div>
    </div>
  )
}
