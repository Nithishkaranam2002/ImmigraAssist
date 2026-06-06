import type { ReactNode } from "react"
import { Loader2, Scale, ExternalLink, AlertTriangle, ListChecks, FileWarning, FileInput } from "lucide-react"
import type { Message } from "@/store/chatStore"
import { cn } from "@/lib/utils"

interface ReferencesPanelProps {
  message: Message | undefined
  isLoading: boolean
  className?: string
}

function outcomeColor(outcome: string | null) {
  if (outcome === "granted") return "border-green-300 text-green-700 bg-green-50"
  if (outcome === "denied") return "border-red-300 text-red-700 bg-red-50"
  if (outcome === "remanded") return "border-yellow-300 text-yellow-700 bg-yellow-50"
  if (outcome === "affirmed") return "border-blue-300 text-blue-700 bg-blue-50"
  return "border-slate-200 text-slate-600"
}

function Section({
  icon: Icon,
  title,
  color,
  children,
}: {
  icon: typeof Scale
  title: string
  color: string
  children: ReactNode
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={cn("w-3.5 h-3.5", color)} />
        <p className="text-xs font-semibold text-slate-700 uppercase tracking-wide">{title}</p>
      </div>
      {children}
    </div>
  )
}

export function ReferencesPanel({ message, isLoading, className }: ReferencesPanelProps) {
  const sortedCases = message?.court_cases
    ? [...message.court_cases].sort((a, b) => {
        const da = a.date_decided || ""
        const db = b.date_decided || ""
        return db.localeCompare(da)
      })
    : []

  return (
    <div className={cn("flex flex-col h-full bg-slate-50/80", className)}>
      <div className="px-4 py-4 border-b border-slate-200 bg-white shrink-0">
        <h2 className="font-semibold text-slate-900 text-sm">References</h2>
        <p className="text-xs text-slate-500 mt-0.5">Sources, forms, and next steps</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {!message ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <Scale className="w-8 h-8 text-slate-300 mb-2" />
            <p className="text-xs text-slate-400 max-w-[200px]">
              Legal clauses and case precedents appear here after you ask a question
            </p>
          </div>
        ) : (
          <>
            {message.next_steps && message.next_steps.length > 0 && (
              <Section icon={ListChecks} title="Next Steps" color="text-brand-500">
                <div className="space-y-2">
                  {message.next_steps.map((step, i) => (
                    <div key={i} className="p-3 bg-white rounded-lg border border-slate-200 text-xs text-slate-700">
                      {step}
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {message.risks && message.risks.length > 0 && (
              <Section icon={FileWarning} title="Risks" color="text-red-500">
                <div className="space-y-2">
                  {message.risks.map((risk, i) => (
                    <div key={i} className="p-3 bg-red-50 rounded-lg border border-red-100 text-xs text-red-900">
                      {risk}
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {message.related_forms && message.related_forms.length > 0 && (
              <Section icon={FileInput} title="Related Forms" color="text-emerald-600">
                <div className="space-y-2">
                  {message.related_forms.map((form, i) => (
                    <div key={i} className="p-3 bg-emerald-50 rounded-lg border border-emerald-100 text-xs text-emerald-900 font-medium">
                      {form}
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {message.important_notes && message.important_notes.length > 0 && (
              <Section icon={AlertTriangle} title="Important Notes" color="text-amber-500">
                <div className="space-y-2">
                  {message.important_notes.map((note, i) => (
                    <div
                      key={i}
                      className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-900 leading-relaxed"
                    >
                      {note}
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {message.cited_laws && message.cited_laws.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-brand-500 shrink-0" />
                  <p className="text-xs font-semibold text-slate-700 uppercase tracking-wide">Legal Clauses</p>
                </div>
                <div className="space-y-2">
                  {message.cited_laws.map((law, i) => (
                    <div key={i} className="p-3 bg-white rounded-lg border border-slate-200 shadow-sm">
                      <p className="text-xs font-medium text-slate-800 leading-relaxed">{law}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {sortedCases.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-violet-500 shrink-0" />
                  <p className="text-xs font-semibold text-slate-700 uppercase tracking-wide">
                    Court Cases (timeline)
                  </p>
                </div>
                <div className="space-y-2">
                  {sortedCases.slice(0, 5).map((c, i) => (
                    <a
                      key={i}
                      href={c.courtlistener_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block p-3 bg-white rounded-lg border border-slate-200 shadow-sm hover:border-violet-300 hover:bg-violet-50 transition-colors group"
                    >
                      <div className="flex items-start justify-between gap-1">
                        <p className="text-xs font-semibold text-slate-800 leading-tight group-hover:text-violet-700 line-clamp-2">
                          {c.case_name}
                        </p>
                        <ExternalLink className="w-3 h-3 text-slate-400 shrink-0 mt-0.5 group-hover:text-violet-500" />
                      </div>
                      {c.citation && (
                        <p className="text-xs text-violet-600 font-mono mt-1">{c.citation}</p>
                      )}
                      <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                        <span className="text-xs text-slate-400">{c.court}</span>
                        {c.date_decided && (
                          <span className="text-xs text-slate-400">· {c.date_decided.slice(0, 10)}</span>
                        )}
                        {c.outcome && (
                          <span className={cn("text-xs px-1.5 py-0.5 rounded border font-medium", outcomeColor(c.outcome))}>
                            {c.outcome}
                          </span>
                        )}
                      </div>
                      {c.summary && (
                        <p className="text-xs text-slate-500 mt-1 line-clamp-3">{c.summary}</p>
                      )}
                    </a>
                  ))}
                </div>
              </div>
            )}

            {sortedCases.length === 0 && message.cited_cases && message.cited_cases.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-violet-500 shrink-0" />
                  <p className="text-xs font-semibold text-slate-700 uppercase tracking-wide">Case Precedents</p>
                </div>
                <div className="space-y-2">
                  {message.cited_cases.slice(0, 5).map((c, i) => {
                    const parts = c.split("|")
                    const label = parts[0]
                    const url = parts[1] || null
                    return url ? (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-start justify-between gap-1 p-3 bg-white rounded-lg border border-slate-200 shadow-sm hover:border-violet-300 hover:bg-violet-50 transition-colors group"
                      >
                        <p className="text-xs font-medium text-slate-800 group-hover:text-violet-700 line-clamp-2">
                          {label}
                        </p>
                        <ExternalLink className="w-3 h-3 text-slate-400 shrink-0 mt-0.5 group-hover:text-violet-500" />
                      </a>
                    ) : (
                      <div key={i} className="p-3 bg-white rounded-lg border border-slate-200 shadow-sm">
                        <p className="text-xs font-medium text-slate-800">{label}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {isLoading && (
              <div className="flex items-center gap-2 text-slate-400 text-xs">
                <Loader2 className="w-3 h-3 animate-spin" />
                Searching cases...
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
