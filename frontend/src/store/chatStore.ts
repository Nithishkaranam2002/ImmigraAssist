import { create } from "zustand"
import type { CourtCase } from "@/services/chatService"
import { generateId } from "@/lib/utils"

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  cited_laws?: string[]
  cited_cases?: string[]
  court_cases?: CourtCase[]
  important_notes?: string[]
  next_steps?: string[]
  risks?: string[]
  related_forms?: string[]
  audit_log_id?: string
  response_time_ms?: number
  visa_type_detected?: string | null
  confidence_score?: number | null
  confidence_level?: string | null
  confidence_label?: string | null
  from_cache?: boolean
  isStreaming?: boolean
  timestamp: Date
}

interface ChatStore {
  messages: Message[]
  isLoading: boolean
  sessionId: string
  matterId: string | null
  compareMode: boolean
  addUserMessage: (content: string) => void
  addAssistantMessage: (data: Partial<Message>) => void
  updateLastAssistant: (data: Partial<Message>) => void
  appendToLastAssistant: (chunk: string) => void
  setLoading: (loading: boolean) => void
  setMatterId: (id: string | null) => void
  setCompareMode: (on: boolean) => void
  clearMessages: () => void
  loadFromHistory: (query: string, data: Partial<Message>) => void
}

function newSessionId(): string {
  return generateId()
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isLoading: false,
  sessionId: newSessionId(),
  matterId: null,
  compareMode: false,

  addUserMessage: (content) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { id: generateId(), role: "user", content, timestamp: new Date() },
      ],
    })),

  addAssistantMessage: (data) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: generateId(),
          role: "assistant",
          content: data.content || "",
          cited_laws: data.cited_laws,
          cited_cases: data.cited_cases,
          court_cases: data.court_cases,
          important_notes: data.important_notes,
          next_steps: data.next_steps,
          risks: data.risks,
          related_forms: data.related_forms,
          audit_log_id: data.audit_log_id,
          response_time_ms: data.response_time_ms,
          visa_type_detected: data.visa_type_detected,
          confidence_score: data.confidence_score,
          confidence_level: data.confidence_level,
          confidence_label: data.confidence_label,
          from_cache: data.from_cache,
          isStreaming: data.isStreaming,
          timestamp: new Date(),
        },
      ],
    })),

  updateLastAssistant: (data) =>
    set((state) => {
      const msgs = [...state.messages]
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "assistant") {
          msgs[i] = { ...msgs[i], ...data, isStreaming: false }
          break
        }
      }
      return { messages: msgs }
    }),

  appendToLastAssistant: (chunk) =>
    set((state) => {
      const msgs = [...state.messages]
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "assistant") {
          msgs[i] = { ...msgs[i], content: msgs[i].content + chunk }
          break
        }
      }
      return { messages: msgs }
    }),

  setLoading: (loading) => set({ isLoading: loading }),
  setMatterId: (id) => set({ matterId: id }),
  setCompareMode: (on) => set({ compareMode: on }),

  clearMessages: () =>
    set({ messages: [], sessionId: newSessionId(), isLoading: false }),

  loadFromHistory: (query, data) =>
    set({
      sessionId: newSessionId(),
      messages: [
        { id: generateId(), role: "user", content: query, timestamp: new Date() },
        {
          id: generateId(),
          role: "assistant",
          content: data.content || "",
          cited_laws: data.cited_laws,
          cited_cases: data.cited_cases,
          court_cases: data.court_cases,
          important_notes: data.important_notes,
          next_steps: data.next_steps,
          risks: data.risks,
          related_forms: data.related_forms,
          audit_log_id: data.audit_log_id,
          response_time_ms: data.response_time_ms,
          visa_type_detected: data.visa_type_detected,
          confidence_score: data.confidence_score,
          confidence_level: data.confidence_level,
          confidence_label: data.confidence_label,
          timestamp: new Date(),
        },
      ],
      isLoading: false,
    }),
}))
