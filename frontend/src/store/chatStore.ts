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
  /** Bumped on clear/history load so in-flight request callbacks can detect staleness. */
  requestGeneration: number
  addUserMessage: (content: string) => string
  addAssistantMessage: (data: Partial<Message> & { id?: string }) => string
  updateAssistant: (id: string, data: Partial<Message>) => void
  appendToAssistant: (id: string, chunk: string) => void
  /** @deprecated Prefer updateAssistant(id, data) — retained for non-request paths. */
  updateLastAssistant: (data: Partial<Message>) => void
  setLoading: (loading: boolean) => void
  setMatterId: (id: string | null) => void
  setCompareMode: (on: boolean) => void
  clearMessages: () => void
  loadFromHistory: (query: string, data: Partial<Message>) => void
  bumpRequestGeneration: () => number
}

function newSessionId(): string {
  return generateId()
}

function assistantFromPartial(data: Partial<Message>, id: string): Message {
  return {
    id,
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
  }
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isLoading: false,
  sessionId: newSessionId(),
  matterId: null,
  compareMode: false,
  requestGeneration: 0,

  addUserMessage: (content) => {
    const id = generateId()
    set((state) => ({
      messages: [
        ...state.messages,
        { id, role: "user", content, timestamp: new Date() },
      ],
    }))
    return id
  },

  addAssistantMessage: (data) => {
    const id = data.id || generateId()
    set((state) => ({
      messages: [...state.messages, assistantFromPartial(data, id)],
    }))
    return id
  },

  updateAssistant: (id, data) =>
    set((state) => {
      const msgs = state.messages.map((m) =>
        m.id === id ? { ...m, ...data, isStreaming: data.isStreaming ?? false } : m
      )
      return { messages: msgs }
    }),

  appendToAssistant: (id, chunk) =>
    set((state) => {
      const msgs = state.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + chunk } : m
      )
      return { messages: msgs }
    }),

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

  setLoading: (loading) => set({ isLoading: loading }),
  setMatterId: (id) => set({ matterId: id }),
  setCompareMode: (on) => set({ compareMode: on }),

  bumpRequestGeneration: () => {
    const next = get().requestGeneration + 1
    set({ requestGeneration: next })
    return next
  },

  clearMessages: () =>
    set((state) => ({
      messages: [],
      sessionId: newSessionId(),
      isLoading: false,
      matterId: null,
      requestGeneration: state.requestGeneration + 1,
    })),

  loadFromHistory: (query, data) =>
    set((state) => ({
      sessionId: newSessionId(),
      requestGeneration: state.requestGeneration + 1,
      messages: [
        { id: generateId(), role: "user", content: query, timestamp: new Date() },
        assistantFromPartial(data, generateId()),
      ],
      isLoading: false,
    })),
}))
