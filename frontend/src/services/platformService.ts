import api from "./api"

export interface HistoryItem {
  id: string
  query: string
  answer_preview: string
  visa_type: string | null
  response_time_ms: number
  confidence_level: string | null
  matter_id: string | null
  created_at: string
}

export interface ResearchHub {
  id: string
  title: string
}

export interface ResearchDetail {
  visa_type: string
  title: string
  description: string
  suggestions: string[]
  forms: string[]
}

export interface ReviewItem {
  id: string
  audit_log_id: string
  query: string
  answer_preview: string
  status: string
  created_at: string
}

export interface PolicyAlert {
  id: string
  title: string
  url: string | null
  source_type: string
  summary: string | null
  is_read: boolean
  created_at: string
}

export interface EvalActivityItem {
  id: string
  query: string
  visa_type: string | null
  confidence_level: string | null
  response_time_ms: number
  from_cache: boolean
  created_at: string
}

export interface EvalMetrics {
  total_queries: number
  queries_today: number
  queries_last_24h: number
  queries_last_hour: number
  avg_response_time_ms: number
  latency_p50_ms: number
  latency_p95_ms: number
  feedback_positive: number
  feedback_negative: number
  satisfaction_rate: number | null
  confidence_distribution: Record<string, number>
  avg_confidence_score: number
  needs_review_count: number
  cache_hits: number
  cache_hit_rate: number
  query_mode_distribution: Record<string, number>
  visa_type_distribution: Record<string, number>
  review_status: Record<string, number>
  pending_reviews: number
  daily_volume: { date: string; count: number }[]
  hourly_activity: { hour: string; count: number }[]
  feedback_trend: { date: string; positive: number; negative: number }[]
  recent_activity: EvalActivityItem[]
  updated_at: string
}

export const platformService = {
  async getHistory(limit = 30, matterId?: string): Promise<HistoryItem[]> {
    const params = new URLSearchParams({ limit: String(limit) })
    if (matterId) params.set("matter_id", matterId)
    const res = await api.get<HistoryItem[]>(`/platform/history?${params}`)
    return res.data
  },

  async getHistoryItem(id: string): Promise<{
    id: string
    query: string
    answer: string
    visa_type: string | null
    response_time_ms: number
    confidence_score: number | null
    confidence_level: string | null
    matter_id: string | null
    session_id: string | null
    next_steps: string[]
    risks: string[]
    related_forms: string[]
  }> {
    const res = await api.get(`/platform/history/${id}`)
    return res.data
  },

  async listResearchHubs(): Promise<ResearchHub[]> {
    const res = await api.get<ResearchHub[]>("/platform/research")
    return res.data
  },

  async getResearchHub(visaType: string): Promise<ResearchDetail> {
    const res = await api.get<ResearchDetail>(`/platform/research/${visaType}`)
    return res.data
  },

  async listReviews(): Promise<ReviewItem[]> {
    const res = await api.get<ReviewItem[]>("/platform/reviews")
    return res.data
  },

  async updateReview(id: string, status: string, notes?: string) {
    const res = await api.patch(`/platform/reviews/${id}`, { status, notes })
    return res.data
  },

  async listAlerts(): Promise<PolicyAlert[]> {
    const res = await api.get<PolicyAlert[]>("/platform/alerts")
    return res.data
  },

  async markAlertRead(id: string) {
    await api.patch(`/platform/alerts/${id}/read`)
  },

  async getEvalMetrics(): Promise<EvalMetrics> {
    const res = await api.get<EvalMetrics>("/platform/eval-metrics")
    return res.data
  },
}
