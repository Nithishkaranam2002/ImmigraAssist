import { useState, useRef, useEffect } from "react"
import { useSearchParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  Send,
  Loader2,
  ThumbsUp,
  ThumbsDown,
  Trash2,
  Sparkles,
  BookOpen,
  PanelRight,
  Download,
  GitCompare,
  FileText,
  ChevronDown,
} from "lucide-react"
import ReactMarkdown from "react-markdown"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { ReferencesPanel } from "@/components/chat/ReferencesPanel"
import { HistorySidebar } from "@/components/chat/HistorySidebar"
import { ConfidenceBadge } from "@/components/chat/ConfidenceBadge"
import { chatService } from "@/services/chatService"
import { matterService } from "@/services/matterService"
import { platformService } from "@/services/platformService"
import { useChatStore } from "@/store/chatStore"
import { useAuthStore } from "@/store/authStore"
import { cn, getApiErrorMessage } from "@/lib/utils"
import { toast } from "@/hooks/useToast"
import { downloadMemo } from "@/lib/exportMemo"
import { canCompare, canDocQA, canExport } from "@/lib/features"

const SUGGESTIONS = [
  "What are the requirements for H4 EAD eligibility?",
  "Explain AC21 portability for H1B holders",
  "What documents are needed for an asylum application?",
  "Compare H1B vs L1 for intracompany transfer",
]

function cleanContent(content: string) {
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

export function ChatPage() {
  const [searchParams] = useSearchParams()
  const [input, setInput] = useState(() => searchParams.get("q") ?? "")
  const [docText, setDocText] = useState("")
  const [showDocQA, setShowDocQA] = useState(false)
  const [feedbackSent, setFeedbackSent] = useState<Set<string>>(new Set())
  const [showReferences, setShowReferences] = useState(false)
  const [historyId, setHistoryId] = useState<string>()
  const bottomRef = useRef<HTMLDivElement>(null)

  const {
    messages,
    isLoading,
    sessionId,
    matterId,
    compareMode,
    addUserMessage,
    addAssistantMessage,
    updateLastAssistant,
    appendToLastAssistant,
    setLoading,
    setMatterId,
    setCompareMode,
    clearMessages,
    loadFromHistory,
  } = useChatStore()
  const { user } = useAuthStore()

  const { data: matters } = useQuery({
    queryKey: ["matters"],
    queryFn: matterService.list,
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isLoading])

  const applyResponse = (response: Awaited<ReturnType<typeof chatService.query>>) => {
    updateLastAssistant({
      content: response.answer,
      cited_laws: response.cited_laws,
      cited_cases: response.cited_cases,
      court_cases: response.court_cases,
      important_notes: response.important_notes,
      next_steps: response.next_steps,
      risks: response.risks,
      related_forms: response.related_forms,
      audit_log_id: response.audit_log_id,
      response_time_ms: response.response_time_ms,
      visa_type_detected: response.visa_type_detected,
      confidence_score: response.confidence_score,
      confidence_level: response.confidence_level,
      confidence_label: response.confidence_label,
      from_cache: response.from_cache,
    })
    setShowReferences(true)
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const query = input.trim()
    setInput("")
    setLoading(true)
    addUserMessage(query)
    addAssistantMessage({ content: "", isStreaming: true })

    const baseReq = {
      query,
      matter_id: matterId || undefined,
      session_id: sessionId,
      query_mode: compareMode ? ("compare" as const) : ("standard" as const),
    }

    try {
      if (showDocQA && docText.trim() && canDocQA(user?.role)) {
        const response = await chatService.docQuery({
          document_text: docText,
          query,
          matter_id: matterId || undefined,
          session_id: sessionId,
        })
        applyResponse(response)
      } else {
        let usedFallback = false
        const runFallback = async (msg: string) => {
          if (usedFallback) {
            updateLastAssistant({ content: msg || "Something went wrong. Please try again." })
            return
          }
          usedFallback = true
          updateLastAssistant({ content: "Generating answer…", isStreaming: false })
          try {
            const response = await chatService.query(baseReq)
            applyResponse(response)
          } catch (err: unknown) {
            updateLastAssistant({
              content: getApiErrorMessage(err, msg || "Something went wrong. Please try again."),
            })
          }
        }

        await chatService.queryStream(baseReq, {
          onChunk: (chunk) => appendToLastAssistant(chunk),
          onDone: (response) => applyResponse(response),
          onError: (msg) => runFallback(msg),
        })
      }
    } catch (err: unknown) {
      updateLastAssistant({
        content: getApiErrorMessage(err, "Something went wrong. Please try again."),
      })
    } finally {
      setLoading(false)
    }
  }

  const handleHistorySelect = async (id: string) => {
    setHistoryId(id)
    try {
      const item = await platformService.getHistoryItem(id)
      loadFromHistory(item.query, {
        content: item.answer,
        next_steps: item.next_steps,
        risks: item.risks,
        related_forms: item.related_forms,
        audit_log_id: item.id,
        response_time_ms: item.response_time_ms,
        visa_type_detected: item.visa_type,
        confidence_score: item.confidence_score,
        confidence_level: item.confidence_level,
        confidence_label: item.confidence_level
          ? `${item.confidence_level} confidence`
          : null,
      })
      setShowReferences(true)
    } catch {
      toast("Failed to load history", "error")
    }
  }

  const handleFeedback = async (auditLogId: string, isPositive: boolean) => {
    if (feedbackSent.has(auditLogId)) return
    try {
      await chatService.submitFeedback({ audit_log_id: auditLogId, is_positive: isPositive })
      setFeedbackSent((prev) => new Set([...prev, auditLogId]))
      toast("Thanks for your feedback!", "success")
    } catch {
      toast("Failed to submit feedback", "error")
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant")

  return (
    <div className="flex h-full relative">
      <HistorySidebar onSelect={handleHistorySelect} activeId={historyId} />

      <div className="flex flex-col flex-1 min-w-0">
        <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-slate-200 bg-white shrink-0 gap-2 flex-wrap">
          <div>
            <h1 className="font-semibold text-slate-900">Legal Research Assistant</h1>
            <p className="text-xs text-slate-500 mt-0.5">USCIS policies · BIA precedents · Court cases</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {matters && matters.length > 0 && (
              <div className="relative">
                <select
                  value={matterId || ""}
                  onChange={(e) => setMatterId(e.target.value || null)}
                  className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 pr-7 bg-white text-slate-700 appearance-none"
                >
                  <option value="">No matter</option>
                  {matters.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.title}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3 h-3 absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              </div>
            )}
            {canCompare(user?.role) && (
              <Button
                variant={compareMode ? "default" : "outline"}
                size="sm"
                onClick={() => setCompareMode(!compareMode)}
              >
                <GitCompare className="w-4 h-4 mr-1" /> Compare
              </Button>
            )}
            {canDocQA(user?.role) && (
              <Button
                variant={showDocQA ? "default" : "outline"}
                size="sm"
                onClick={() => setShowDocQA((v) => !v)}
              >
                <FileText className="w-4 h-4 mr-1" /> Doc Q&A
              </Button>
            )}
            {lastAssistant && canExport(user?.role) && (
              <Button variant="outline" size="sm" onClick={() => downloadMemo(messages)}>
                <Download className="w-4 h-4 mr-1" /> Export
              </Button>
            )}
            {lastAssistant && (
              <Button
                variant="outline"
                size="sm"
                className="lg:hidden"
                onClick={() => setShowReferences((v) => !v)}
              >
                <PanelRight className="w-4 h-4 mr-1.5" />
                Sources
              </Button>
            )}
            {messages.length > 0 && (
              <Button variant="ghost" size="sm" onClick={clearMessages}>
                <Trash2 className="w-4 h-4 mr-1" /> Clear
              </Button>
            )}
          </div>
        </div>

        {showDocQA && canDocQA(user?.role) && (
          <div className="px-4 sm:px-6 py-3 border-b border-slate-200 bg-amber-50/50">
            <p className="text-xs text-amber-800 mb-2 font-medium">
              Paste client document text (petition draft, cover letter, etc.)
            </p>
            <Textarea
              value={docText}
              onChange={(e) => setDocText(e.target.value)}
              placeholder="Paste document content here..."
              className="text-xs min-h-[80px] bg-white"
              rows={3}
            />
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in px-4">
              <div className="w-16 h-16 bg-brand-50 rounded-2xl flex items-center justify-center mb-5 ring-1 ring-brand-100">
                <Sparkles className="w-8 h-8 text-brand-600" />
              </div>
              <h2 className="text-xl font-bold text-slate-900 mb-2">How can I help you today?</h2>
              <p className="text-slate-500 text-sm max-w-lg leading-relaxed">
                Ask about H1B, H4 EAD, asylum, green cards, USCIS policy manual sections,
                and immigration case precedents — every answer includes cited sources.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mt-8 w-full max-w-2xl">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => setInput(suggestion)}
                    className="text-left px-4 py-3.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-600 hover:bg-brand-50 hover:border-brand-200 hover:text-brand-700 transition-all shadow-sm"
                  >
                    <BookOpen className="w-3.5 h-3.5 inline mr-2 text-brand-500 opacity-70" />
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message, idx) => (
            <div
              key={message.id}
              className={cn(
                "flex animate-slide-up",
                message.role === "user" ? "justify-end" : "justify-start"
              )}
              style={{ animationDelay: `${idx * 30}ms` }}
            >
              <div className={cn(message.role === "user" ? "max-w-lg" : "w-full max-w-3xl")}>
                {message.role === "user" ? (
                  <div className="bg-brand-600 text-white rounded-2xl rounded-tr-md px-4 py-3 text-sm shadow-sm">
                    {message.content}
                  </div>
                ) : (
                  <div className="bg-white rounded-2xl rounded-tl-md border border-slate-200 shadow-sm overflow-hidden">
                    <div className="px-5 py-4">
                      <div className="flex flex-wrap items-center gap-2 mb-3">
                        {message.visa_type_detected && (
                          <Badge variant="secondary">{message.visa_type_detected.toUpperCase()}</Badge>
                        )}
                        <ConfidenceBadge
                          level={message.confidence_level}
                          label={message.confidence_label}
                          fromCache={message.from_cache}
                        />
                        {message.isStreaming && (
                          <Badge variant="outline" className="text-xs animate-pulse">
                            Streaming...
                          </Badge>
                        )}
                      </div>
                      <div className="prose-chat">
                        <ReactMarkdown>{cleanContent(message.content)}</ReactMarkdown>
                      </div>
                      {!message.isStreaming &&
                        (message.cited_laws?.length ||
                          message.cited_cases?.length ||
                          message.court_cases?.length) ? (
                        <p className="mt-4 text-xs text-slate-500 border-t border-slate-100 pt-3">
                          Based on{" "}
                          {[
                            message.cited_laws?.length
                              ? `${message.cited_laws.length} policy source${message.cited_laws.length !== 1 ? "s" : ""}`
                              : null,
                            message.cited_cases?.length
                              ? `${message.cited_cases.length} case precedent${message.cited_cases.length !== 1 ? "s" : ""}`
                              : null,
                            message.court_cases?.length
                              ? `${message.court_cases.length} court decision${message.court_cases.length !== 1 ? "s" : ""}`
                              : null,
                          ]
                            .filter(Boolean)
                            .join(", ")}
                          . See References panel for citations, forms, and next steps.
                        </p>
                      ) : null}
                      {!message.isStreaming &&
                      message.important_notes &&
                      message.important_notes.length > 0 ? (
                        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50/80 p-3">
                          <p className="text-xs font-semibold text-amber-900 mb-2">
                            Important notes &amp; verification items
                          </p>
                          <ul className="space-y-1.5">
                            {message.important_notes.slice(0, 5).map((note, i) => (
                              <li key={i} className="text-xs text-amber-900 leading-relaxed flex gap-2">
                                <span className="text-amber-500 shrink-0">•</span>
                                <span>{note}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                    {message.audit_log_id && !message.isStreaming && (
                      <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between bg-slate-50/50">
                        <span className="text-xs text-slate-400">
                          {(message.response_time_ms ?? 0) > 0
                            ? `${(message.response_time_ms! / 1000).toFixed(1)}s`
                            : "—"}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-slate-400">Helpful?</span>
                          <button
                            type="button"
                            onClick={() => handleFeedback(message.audit_log_id!, true)}
                            disabled={feedbackSent.has(message.audit_log_id)}
                            className={cn(
                              "p-1 rounded hover:bg-green-50 transition-colors",
                              feedbackSent.has(message.audit_log_id)
                                ? "opacity-50"
                                : "text-slate-400 hover:text-green-600"
                            )}
                          >
                            <ThumbsUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleFeedback(message.audit_log_id!, false)}
                            disabled={feedbackSent.has(message.audit_log_id)}
                            className={cn(
                              "p-1 rounded hover:bg-red-50 transition-colors",
                              feedbackSent.has(message.audit_log_id)
                                ? "opacity-50"
                                : "text-slate-400 hover:text-red-500"
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

          {isLoading && messages[messages.length - 1]?.role !== "assistant" && (
            <div className="flex justify-start animate-fade-in">
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-md px-5 py-4 shadow-sm">
                <div className="flex items-center gap-3 text-slate-500 text-sm">
                  <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
                  <span>Searching policies and case law...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="px-4 sm:px-6 py-4 border-t border-slate-200 bg-white shrink-0">
          <div className="flex gap-3 items-end max-w-3xl mx-auto lg:mx-0">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                compareMode
                  ? "Compare visa pathways (e.g. H1B vs L1 for this scenario)..."
                  : "Ask about visa requirements, USCIS policies, case precedents..."
              }
              className="flex-1 min-h-[48px] max-h-32 resize-none rounded-xl border-slate-200 focus-visible:ring-brand-500"
              rows={1}
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              size="icon"
              className="h-11 w-11 rounded-xl shrink-0"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
          <p className="text-xs text-slate-400 text-center mt-2">
            Enter to send · Shift+Enter for new line · Signed in as {user?.full_name}
          </p>
        </div>
      </div>

      <div className="hidden lg:flex w-80 shrink-0 border-l border-slate-200 flex-col">
        <ReferencesPanel message={lastAssistant} isLoading={isLoading} />
      </div>

      {showReferences && (
        <>
          <button
            type="button"
            aria-label="Close references"
            className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden"
            onClick={() => setShowReferences(false)}
          />
          <div className="fixed inset-y-0 right-0 z-50 w-[min(100%,20rem)] lg:hidden flex flex-col shadow-2xl">
            <ReferencesPanel message={lastAssistant} isLoading={isLoading} />
          </div>
        </>
      )}
    </div>
  )
}
