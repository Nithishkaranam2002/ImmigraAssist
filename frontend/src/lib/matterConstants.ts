export const MATTER_VISA_OPTIONS = [
  { value: "", label: "Select visa type" },
  { value: "h1b", label: "H-1B" },
  { value: "h4", label: "H-4" },
  { value: "h4_ead", label: "H-4 EAD" },
  { value: "l1", label: "L-1" },
  { value: "o1", label: "O-1" },
  { value: "eb1", label: "EB-1" },
  { value: "eb2", label: "EB-2" },
  { value: "f1", label: "F-1" },
  { value: "asylum", label: "Asylum" },
  { value: "green_card", label: "Green card" },
] as const

export const MATTER_DESCRIPTION_MAX = 2000

export const MATTER_DESCRIPTION_HINT =
  "1–3 sentences is enough. Include: client role, principal's status (e.g. I-140/AC21), location (in US/abroad), and goal."

export const MATTER_DESCRIPTION_PLACEHOLDER =
  "e.g. Maria Garcia, H-4 spouse of John Smith (H-1B). Principal has approved I-140. In US on H-4; wants EAD. Not a renewal."

export const MATTER_QUICK_PROMPTS = [
  "What documents are required for this client?",
  "What forms need to be filed?",
  "What are the eligibility requirements?",
  "What are the risks and denial scenarios?",
] as const

export function matterStatusLabel(status: string): string {
  if (status === "on_hold") return "On hold"
  if (status === "closed") return "Closed"
  return "Active"
}

export function matterStatusClass(status: string): string {
  if (status === "on_hold") return "bg-amber-50 text-amber-800 border-amber-200"
  if (status === "closed") return "bg-slate-100 text-slate-600 border-slate-200"
  return "bg-emerald-50 text-emerald-800 border-emerald-200"
}
