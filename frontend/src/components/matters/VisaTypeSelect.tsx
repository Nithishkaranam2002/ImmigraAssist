import { MATTER_VISA_OPTIONS } from "@/lib/matterConstants"
import { cn } from "@/lib/utils"

interface VisaTypeSelectProps {
  value: string
  onChange: (value: string) => void
  className?: string
}

export function VisaTypeSelect({ value, onChange, className }: VisaTypeSelectProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        "w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-700",
        className
      )}
    >
      {MATTER_VISA_OPTIONS.map((opt) => (
        <option key={opt.value || "empty"} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  )
}
