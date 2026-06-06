import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface ConfidenceBadgeProps {
  level: string | null | undefined
  label: string | null | undefined
  fromCache?: boolean
}

export function ConfidenceBadge({ level, label, fromCache }: ConfidenceBadgeProps) {
  if (!level && !label) return null

  const colors: Record<string, string> = {
    high: "bg-emerald-50 text-emerald-700 border-emerald-200",
    medium: "bg-amber-50 text-amber-800 border-amber-200",
    low: "bg-red-50 text-red-700 border-red-200",
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <Badge
        variant="outline"
        className={cn("text-xs font-medium", colors[level || "medium"] || colors.medium)}
      >
        {label || level}
      </Badge>
      {fromCache && (
        <Badge variant="secondary" className="text-xs">
          Cached
        </Badge>
      )}
    </div>
  )
}
