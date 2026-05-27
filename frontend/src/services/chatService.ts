import api from "./api"

interface QueryRequest {
  query: string
  stream?: boolean
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
  audit_log_id: string
  response_time_ms: number
  visa_type_detected: string | null
}

export const chatService = {
  async query(data: QueryRequest): Promise<QueryResponse> {
    const response = await api.post<QueryResponse>("/chat/query", data)
    return response.data
  },

  async submitFeedback(data: {
    audit_log_id: string
    is_positive: boolean
  }) {
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