import api from "./api"
import { formatApiDetail } from "@/lib/utils"

export interface QueryRequest {
  query: string
  stream?: boolean
  matter_id?: string
  session_id?: string
  query_mode?: "standard" | "compare"
}

export interface CourtCase {
  case_name: string
  case_id: string
  court: string
  date_decided: string | null
  citation: string | null
  summary: string | null
  courtlistener_url: string
  visa_types: string[]
  outcome: string | null
  relevance_score: number
}

export interface QueryResponse {
  answer: string
  cited_laws: string[]
  cited_cases: string[]
  court_cases: CourtCase[]
  important_notes: string[]
  next_steps: string[]
  risks: string[]
  related_forms: string[]
  audit_log_id: string
  response_time_ms: number
  visa_type_detected: string | null
  confidence_score: number | null
  confidence_level: string | null
  confidence_label: string | null
  from_cache: boolean
  session_id: string | null
  matter_id: string | null
}

export interface StreamCallbacks {
  onChunk: (text: string) => void
  onDone: (response: QueryResponse) => void
  /** May return a Promise so callers can finish fallback work before stream settles. */
  onError: (message: string) => void | Promise<void>
}

function streamErrorMessage(status: number, detail: unknown): string {
  if (status === 401) return "Session expired. Please log in again."
  if (status === 429) return "Too many requests. Please wait a moment and try again."
  if (status === 502 || status === 503 || status === 504) {
    return "Server is starting up. Please wait 30 seconds and try again."
  }
  return formatApiDetail(detail, "Request failed")
}

export const chatService = {
  async query(data: QueryRequest): Promise<QueryResponse> {
    const response = await api.post<QueryResponse>("/chat/query", { ...data, stream: false })
    return response.data
  },

  async queryStream(data: QueryRequest, callbacks: StreamCallbacks): Promise<void> {
    const emitError = async (message: string) => {
      await Promise.resolve(callbacks.onError(message))
    }

    const token = localStorage.getItem("access_token")
    if (!token) {
      await emitError("Session expired. Please log in again.")
      return
    }

    const res = await fetch("/api/v1/chat/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ ...data, stream: true }),
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }))
      await emitError(streamErrorMessage(res.status, err.detail))
      return
    }

    const reader = res.body?.getReader()
    if (!reader) {
      await emitError("No response stream")
      return
    }

    const decoder = new TextDecoder()
    let buffer = ""
    let completed = false

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue
        const payload = line.slice(6).trim()
        if (payload === "[DONE]") {
          if (!completed) {
            await emitError("Response ended unexpectedly. Retrying…")
          }
          return
        }

        try {
          const event = JSON.parse(payload)
          if (event.type === "chunk") {
            callbacks.onChunk(event.content)
          } else if (event.type === "done") {
            completed = true
            callbacks.onDone(event as QueryResponse)
          } else if (event.type === "error") {
            await emitError(event.message || "Something went wrong. Please try again.")
            return
          }
        } catch {
          // skip malformed lines
        }
      }
    }

    if (!completed) {
      await emitError("Response ended unexpectedly. Retrying…")
    }
  },

  async docQuery(data: {
    document_text: string
    query: string
    matter_id?: string
    session_id?: string
  }): Promise<QueryResponse> {
    const response = await api.post<QueryResponse>("/chat/doc-query", data)
    return response.data
  },

  async submitFeedback(data: { audit_log_id: string; is_positive: boolean }) {
    const response = await api.post("/feedback/", data)
    return response.data
  },

  async searchCases(query: string, visaType?: string) {
    const params = new URLSearchParams({ q: query, max_results: "5" })
    if (visaType) params.append("visa_type", visaType)
    const response = await api.get(`/cases/search?${params}`)
    return response.data
  },
}
