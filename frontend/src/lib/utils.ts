import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Works on HTTP — crypto.randomUUID() requires HTTPS in Safari/Chrome */
export function getApiErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === "object" && "response" in err) {
    const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
    if (typeof detail === "string") return detail
  }
  return fallback
}

export function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    try {
      return crypto.randomUUID()
    } catch {
      // non-secure context (plain HTTP)
    }
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
}
