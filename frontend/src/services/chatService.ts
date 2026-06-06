import api from "./api"

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
  onError: (message: string) => void
}

export const chatService = {
  async query(data: QueryRequest): Promise<QueryResponse> {
    const response = await api.post<QueryResponse>("/chat/query", data)
    return response.data
  },

  async queryStream(data: QueryRequest, callbacks: StreamCallbacks): Promise<void> {
    const token = localStorage.getItem("access_token")
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
      callbacks.onError(err.detail || "Request failed")
      return
    }

    const reader = res.body?.getReader()
    if (!reader) {
      callbacks.onError("No response stream")
      return
    }

    const decoder = new TextDecoder()
    let buffer = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue
        const payload = line.slice(6).trim()
        if (payload === "[DONE]") return

        try {
          const event = JSON.parse(payload)
          if (event.type === "chunk") {
            callbacks.onChunk(event.content)
          } else if (event.type === "done") {
            const { type: _, ...response } = event
            callbacks.onDone(response as QueryResponse)
          } else if (event.type === "error") {
            callbacks.onError(event.message)
          }
        } catch {
          // skip malformed lines
        }
      }
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
