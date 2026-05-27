export interface User {
  id: string
  full_name: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export type UserRole =
  | "super_admin"
  | "admin"
  | "attorney"
  | "junior_associate"

export interface AuthResponse {
  access_token: string
  token_type: string
  user_id: string
  role: UserRole
  full_name: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  full_name: string
  email: string
  password: string
  role: UserRole
}

export interface QueryRequest {
  query: string
  stream?: boolean
}

export interface QueryResponse {
  answer: string
  cited_laws: string[]
  cited_cases: string[]
  important_notes: string[]
  audit_log_id: string
  response_time_ms: number
  visa_type_detected: string | null
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  cited_laws?: string[]
  cited_cases?: string[]
  important_notes?: string[]
  audit_log_id?: string
  response_time_ms?: number
  visa_type_detected?: string | null
  timestamp: Date
}

export interface Document {
  id: string
  filename: string
  doc_type: "law" | "case"
  status: "pending" | "processing" | "completed" | "failed"
  version: number
  visa_type: string | null
  total_chunks: number
  uploaded_by: string
  created_at: string
}

export interface FeedbackRequest {
  audit_log_id: string
  is_positive: boolean
  comment?: string
}

export interface SystemStats {
  total_users: number
  documents: Record<string, number>
  total_chunks_indexed: number
  total_queries: number
  feedback: {
    positive: number
    negative: number
    satisfaction_rate: number | null
  }
}

export interface SystemHealth {
  postgresql: string
  milvus_laws: string
  milvus_cases: string
  overall: string
}

export interface AuditLog {
  id: string
  user_id: string
  query: string
  visa_type_detected: string | null
  response_time_ms: number
  token_count: number
  created_at: string
}
