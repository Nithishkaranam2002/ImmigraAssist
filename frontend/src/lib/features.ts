import type { UserRole } from "@/types"

const hierarchy: Record<UserRole, number> = {
  super_admin: 4,
  admin: 3,
  attorney: 2,
  junior_associate: 1,
}

function atLeast(role: UserRole | undefined, min: UserRole): boolean {
  if (!role) return false
  return hierarchy[role] >= hierarchy[min]
}

export function canExport(role: UserRole | undefined): boolean {
  return atLeast(role, "attorney")
}

export function canManageMatters(role: UserRole | undefined): boolean {
  return atLeast(role, "junior_associate")
}

export function canCompare(role: UserRole | undefined): boolean {
  return atLeast(role, "junior_associate")
}

export function canDocQA(role: UserRole | undefined): boolean {
  return atLeast(role, "attorney")
}

export function canReviewQueue(role: UserRole | undefined): boolean {
  return atLeast(role, "attorney")
}

export function canEvalDashboard(role: UserRole | undefined): boolean {
  return atLeast(role, "admin")
}

export function canPolicyAlerts(role: UserRole | undefined): boolean {
  return atLeast(role, "admin")
}
