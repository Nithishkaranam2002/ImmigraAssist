import { queryClient } from "@/lib/queryClient"
import { useChatStore } from "@/store/chatStore"

/**
 * Drop in-memory UI state that belongs to the previous authenticated user.
 * SPA logout does not reload the page, so zustand + React Query otherwise
 * keep the prior user's chat, matter selection, and cached lists.
 */
export function resetClientState(): void {
  useChatStore.getState().clearMessages()
  useChatStore.getState().setCompareMode(false)
  queryClient.clear()
}
