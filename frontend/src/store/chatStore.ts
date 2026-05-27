import { create } from "zustand"
import type { CourtCase } from "@/services/chatService"

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  cited_laws?: string[]
  cited_cases?: string[]
  court_cases?: CourtCase[]
  important_notes?: string[]
  audit_log_id?: string
  response_time_ms?: number
  visa_type_detected?: string | null
  timestamp: Date
}

interface ChatStore {
  messages: Message[]
  isLoading: boolean
  addUserMessage: (content: string) => void
  addAssistantMessage: (data: Partial<Message>) => void
  setLoading: (loading: boolean) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isLoading: false,

  addUserMessage: (content) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: crypto.randomUUID(),
          role: "user",
          content,
          timestamp: new Date(),
        },
      ],
    })),

  addAssistantMessage: (data) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.content || "",
          cited_laws: data.cited_laws,
          cited_cases: data.cited_cases,
          court_cases: data.court_cases,
          important_notes: data.important_notes,
          audit_log_id: data.audit_log_id,
          response_time_ms: data.response_time_ms,
          visa_type_detected: data.visa_type_detected,
          timestamp: new Date(),
        },
      ],
    })),

  setLoading: (loading) => set({ isLoading: loading }),
  clearMessages: () => set({ messages: [] }),
}))