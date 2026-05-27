import { useState, useRef, useEffect } from "react"
import { Send, Loader2, ThumbsUp, ThumbsDown, Trash2, Scale, ExternalLink } from "lucide-react"
import ReactMarkdown from "react-markdown"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { chatService } from "@/services/chatService"
import { useChatStore } from "@/store/chatStore"
import { useAuthStore } from "@/store/authStore"
import { cn } from "@/lib/utils"
import type { CourtCase } from "@/services/chatService"

export function ChatPage() {
  const [input, setInput] = useState("")
  const [feedbackSent, setFeedbackSent] = useState<Set<string>>(new Set())
  const bottomRef = useRef<HTMLDivElement>(null)
  const { messages, isLoading, addUserMessage, addAssistantMessage, setLoading, clearMessages } = useChatStore()
  const { user } = useAuthStore()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const query = input.trim()
    setInput("")
    addUserMessage(query)
    setLoading(true)
    try {
      const response = await chatService.query({ query })
      addAssistantMessage({
        content: response.answer,
        cited_laws: response.cited_laws,
        cited_cases: response.cited_cases,
        court_cases: response.court_cases,
        important_notes: response.important_notes,
        audit_log_id: response.audit_log_id,
        response_time_ms: response.response_time_ms,
        visa_type_detected: response.visa_type_detected,
      })
    } catch (err: any) {
      addAssistantMessage({
        content: err.response?.data?.detail || "Something went wrong. Please try again.",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = async (auditLogId: string, isPositive: boolean) => {
    if (feedbackSent.has(auditLogId)) return
    try {
      await chatService.submitFeedback({ audit_log_id: auditLogId, is_positive: isPositive })
      setFeedbackSent(prev => new Set([...prev, auditLogId]))
    } catch {}
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const cleanContent = (content: string) => {
    return content
      .replace(/\bcertain\s+the applicant/g, "certain applicants")
      .replace(/\beligible\s+the applicant/g, "eligible applicants")
      .replace(/\bthe the applicant/g, "the applicant")
      .replace(/\ban the applicant/g, "the applicant")
      .replace(/\ba the applicant/g, "the applicant")
      .replace(/\bprove your the applicant\b/g, "prove your identity")
      .replace(/\[REDACTED-[A-Z_]+\]/g, "the applicant")
      .replace(/\[Protected\]/g, "the applicant")
  }

  const outcomeColor = (outcome: string | null) => {
    if (outcome === "granted") return "border-green-300 text-green-700 bg-green-50"
    if (outcome === "denied") return "border-red-300 text-red-700 bg-red-50"
    if (outcome === "remanded") return "border-yellow-300 text-yellow-700 bg-yellow-50"
    if (outcome === "affirmed") return "border-blue-300 text-blue-700 bg-blue-50"
    return "border-gray-300 text-gray-600"
  }

  const lastAssistant = [...messages].reverse().find(m => m.role === "assistant")

  return (
    <div className="flex h-full">

      {/* ── LEFT: Chat ──────────────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white">
          <div>
            <h1 className="font-semibold text-gray-900">Legal Research Assistant</h1>
            <p className="text-xs text-gray-500">Ask anything about US immigration law</p>
          </div>
          {messages.length > 0 && (
            <Button variant="ghost" size="sm" onClick={clearMessages}>
              <Trash2 className="w-4 h-4 mr-1" /> Clear
            </Button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mb-4">
                <Scale className="w-8 h-8 text-blue-600" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">ImmigraAssist</h2>
              <p className="text-gray-500 text-sm max-w-md">
                Ask questions about H1B, H4 EAD, asylum, green card processes, USCIS policies, and past case precedents.
              </p>
              <div className="grid grid-cols-1 gap-2 mt-6 w-full max-w-lg">
                {[
                  "What are the requirements for H4 EAD eligibility?",
                  "Explain AC21 portability for H1B holders",
                  "What documents are needed for asylum application?",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                    className="text-left px-4 py-3 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}
            >
              <div className={cn(message.role === "user" ? "max-w-lg" : "w-full")}>
                {message.role === "user" ? (
                  <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm">
                    {message.content}
                  </div>
                ) : (
                  <div className="bg-white rounded-2xl rounded-tl-sm border border-gray-200 shadow-sm overflow-hidden">
                    <div className="px-5 py-4">
                      {message.visa_type_detected && (
                        <Badge variant="secondary" className="mb-3">
                          {message.visa_type_detected.toUpperCase()}
                        </Badge>
                      )}
                      <div className="text-sm text-gray-800 leading-relaxed [&>p]:mb-3 [&>ul]:mb-3 [&>ul]:list-disc [&>ul]:pl-5 [&>ul>li]:mb-1 [&>ol]:mb-3 [&>ol]:list-decimal [&>ol]:pl-5 [&>ol>li]:mb-1 [&>h1]:text-base [&>h1]:font-bold [&>h1]:mb-2 [&>h2]:text-base [&>h2]:font-bold [&>h2]:mb-2 [&>h3]:text-sm [&>h3]:font-semibold [&>h3]:mb-2 [&>strong]:font-semibold [&>hr]:my-3 [&>hr]:border-gray-200">
                        <ReactMarkdown>{cleanContent(message.content)}</ReactMarkdown>
                      </div>
                    </div>
                    {message.audit_log_id && (
                      <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
                        <span className="text-xs text-gray-400">{message.response_time_ms}ms</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-400">Helpful?</span>
                          <button
                            onClick={() => handleFeedback(message.audit_log_id!, true)}
                            disabled={feedbackSent.has(message.audit_log_id)}
                            className={cn(
                              "p-1 rounded hover:bg-green-50 transition-colors",
                              feedbackSent.has(message.audit_log_id) ? "opacity-50" : "text-gray-400 hover:text-green-600"
                            )}
                          >
                            <ThumbsUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleFeedback(message.audit_log_id!, false)}
                            disabled={feedbackSent.has(message.audit_log_id)}
                            className={cn(
                              "p-1 rounded hover:bg-red-50 transition-colors",
                              feedbackSent.has(message.audit_log_id) ? "opacity-50" : "text-gray-400 hover:text-red-500"
                            )}
                          >
                            <ThumbsDown className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm">
                <div className="flex items-center gap-2 text-gray-500 text-sm">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Searching policies and cases...
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="px-6 py-4 border-t border-gray-200 bg-white">
          <div className="flex gap-3 items-end">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about immigration policies, visa requirements, case precedents..."
              className="flex-1 min-h-[44px] max-h-32"
              rows={1}
            />
            <Button onClick={handleSend} disabled={!input.trim() || isLoading} size="icon">
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
          <p className="text-xs text-gray-400 text-center mt-2">
            Press Enter to send · Shift+Enter for new line · {user?.full_name}
          </p>
        </div>
      </div>

      {/* ── RIGHT: References Panel ──────────────────────────────────── */}
      <div className="w-80 shrink-0 bg-gray-50 border-l border-gray-200 flex flex-col">
        <div className="px-4 py-4 border-b border-gray-200 bg-white shrink-0">
          <h2 className="font-semibold text-gray-900 text-sm">References</h2>
          <p className="text-xs text-gray-500 mt-0.5">Laws and cases from last answer</p>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!lastAssistant ? (
            <div className="flex flex-col items-center justify-center h-48 text-center">
              <Scale className="w-8 h-8 text-gray-300 mb-2" />
              <p className="text-xs text-gray-400">
                References will appear here after you ask a question
              </p>
            </div>
          ) : (
            <>
              {/* Legal Clauses */}
              {lastAssistant.cited_laws && lastAssistant.cited_laws.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-blue-500 shrink-0"></div>
                    <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                      Legal Clauses
                    </p>
                  </div>
                  <div className="space-y-2">
                    {lastAssistant.cited_laws.map((law, i) => (
                      <div key={i} className="p-3 bg-white rounded-lg border border-gray-200 shadow-sm">
                        <p className="text-xs font-medium text-gray-800">{law}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* CourtListener Live Cases */}
              {lastAssistant.court_cases && lastAssistant.court_cases.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-purple-500 shrink-0"></div>
                    <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                      Related Cases
                    </p>
                  </div>
                  <div className="space-y-2">
                    {lastAssistant.court_cases.slice(0, 5).map((c, i) => (
                      
                        <a key={i}
                        href={c.courtlistener_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block p-3 bg-white rounded-lg border border-gray-200 shadow-sm hover:border-purple-300 hover:bg-purple-50 transition-colors group"
                      >
                        <div className="flex items-start justify-between gap-1">
                          <p className="text-xs font-semibold text-gray-800 leading-tight group-hover:text-purple-700 line-clamp-2">
                            {c.case_name}
                          </p>
                          <ExternalLink className="w-3 h-3 text-gray-400 shrink-0 mt-0.5 group-hover:text-purple-500" />
                        </div>
                        {c.citation && (
                          <p className="text-xs text-purple-600 font-mono mt-1">{c.citation}</p>
                        )}
                        <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                          <span className="text-xs text-gray-400">{c.court}</span>
                          {c.date_decided && (
                            <span className="text-xs text-gray-400">· {c.date_decided.slice(0, 4)}</span>
                          )}
                          {c.outcome && (
                            <span className={`text-xs px-1.5 py-0.5 rounded border font-medium ${outcomeColor(c.outcome)}`}>
                              {c.outcome}
                            </span>
                          )}
                        </div>
                        {c.summary && (
                          <p className="text-xs text-gray-500 mt-1 line-clamp-3">{c.summary}</p>
                        )}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Milvus BIA/AAO Case Precedents */}
              {(!lastAssistant.court_cases || lastAssistant.court_cases.length === 0) &&
                lastAssistant.cited_cases && lastAssistant.cited_cases.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-purple-500 shrink-0"></div>
                    <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                      Case Precedents
                    </p>
                  </div>
                  <div className="space-y-2">
                    {lastAssistant.cited_cases.slice(0, 5).map((c, i) => {
                      const parts = c.split("|")
                      const label = parts[0]
                      const url = parts[1] || null
                      return url ? (
                        
                          <a key={i}
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-start justify-between gap-1 p-3 bg-white rounded-lg border border-gray-200 shadow-sm hover:border-purple-300 hover:bg-purple-50 transition-colors group"
                        >
                          <p className="text-xs font-medium text-gray-800 group-hover:text-purple-700 line-clamp-2">
                            {label}
                          </p>
                          <ExternalLink className="w-3 h-3 text-gray-400 shrink-0 mt-0.5 group-hover:text-purple-500" />
                        </a>
                      ) : (
                        <div key={i} className="p-3 bg-white rounded-lg border border-gray-200 shadow-sm">
                          <p className="text-xs font-medium text-gray-800">{label}</p>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {isLoading && (
                <div className="flex items-center gap-2 text-gray-400 text-xs">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Searching cases...
                </div>
              )}
            </>
          )}
        </div>
      </div>

    </div>
  )
}