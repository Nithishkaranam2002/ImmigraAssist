import { useQuery } from "@tanstack/react-query"
import { Clock, Loader2 } from "lucide-react"
import { platformService } from "@/services/platformService"
import { cn } from "@/lib/utils"

interface HistorySidebarProps {
  onSelect: (id: string) => void
  activeId?: string
}

export function HistorySidebar({ onSelect, activeId }: HistorySidebarProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["query-history"],
    queryFn: () => platformService.getHistory(25),
  })

  return (
    <div className="flex flex-col h-full bg-white border-r border-slate-200 w-56 shrink-0 hidden xl:flex">
      <div className="px-3 py-3 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wide">
            Recent Research
          </h3>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {isLoading && (
          <div className="flex justify-center py-6">
            <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
          </div>
        )}
        {!isLoading && (!data || data.length === 0) && (
          <p className="text-xs text-slate-400 text-center py-6 px-2">No history yet</p>
        )}
        {data?.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelect(item.id)}
            className={cn(
              "w-full text-left px-2.5 py-2 rounded-lg text-xs transition-colors",
              activeId === item.id
                ? "bg-brand-50 text-brand-800 border border-brand-200"
                : "text-slate-600 hover:bg-slate-50"
            )}
          >
            <p className="line-clamp-2 font-medium leading-snug">{item.query}</p>
            <div className="flex items-center gap-1.5 mt-1 text-slate-400">
              {item.visa_type && <span className="uppercase">{item.visa_type}</span>}
              {item.confidence_level && (
                <>
                  <span>·</span>
                  <span className="capitalize">{item.confidence_level}</span>
                </>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
