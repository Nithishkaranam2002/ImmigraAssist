import { useNavigate, useParams, Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, Loader2, MessageSquare } from "lucide-react"
import { platformService } from "@/services/platformService"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

export function ResearchVisaPage() {
  const { visaType } = useParams<{ visaType: string }>()
  const navigate = useNavigate()

  const { data, isLoading, error } = useQuery({
    queryKey: ["research", visaType],
    queryFn: () => platformService.getResearchHub(visaType!),
    enabled: !!visaType,
  })

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="p-6 text-center">
        <p className="text-slate-500">Visa type not found</p>
        <Link to="/research" className="text-brand-600 text-sm mt-2 inline-block">
          Back to hubs
        </Link>
      </div>
    )
  }

  const ask = (q: string) => {
    navigate("/chat", { state: { prefilledQuery: q } })
  }

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 max-w-3xl">
      <Link to="/research" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600 mb-4">
        <ArrowLeft className="w-4 h-4" /> All hubs
      </Link>

      <h1 className="text-2xl font-bold text-slate-900">{data.title}</h1>
      <p className="text-slate-600 mt-2 leading-relaxed">{data.description}</p>

      {data.forms.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-4">
          {data.forms.map((f) => (
            <Badge key={f} variant="secondary">
              {f}
            </Badge>
          ))}
        </div>
      )}

      <h2 className="font-semibold text-slate-900 mt-8 mb-3">Suggested questions</h2>
      <div className="space-y-2">
        {data.suggestions.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => ask(s)}
            className="w-full text-left px-4 py-3.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-700 hover:bg-brand-50 hover:border-brand-200 transition-all flex items-center gap-3"
          >
            <MessageSquare className="w-4 h-4 text-brand-500 shrink-0" />
            {s}
          </button>
        ))}
      </div>

      <Button className="mt-6" onClick={() => navigate("/chat")}>
        Open Research Chat
      </Button>
    </div>
  )
}
