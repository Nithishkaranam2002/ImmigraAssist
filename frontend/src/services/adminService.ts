import api from "./api"
import type { SystemStats, SystemHealth, AuditLog, User } from "@/types"

export const adminService = {
  async getHealth(): Promise<SystemHealth> {
    const response = await api.get<SystemHealth>("/admin/health")
    return response.data
  },

  async getStats(): Promise<SystemStats> {
    const response = await api.get<SystemStats>("/admin/stats")
    return response.data
  },

  async getAuditLogs(): Promise<AuditLog[]> {
    const response = await api.get<AuditLog[]>("/admin/audit-logs")
    return response.data
  },

  async listUsers(): Promise<User[]> {
    const response = await api.get<User[]>("/users/")
    return response.data
  },

  async updateUserRole(userId: string, role: string) {
    const response = await api.patch(`/users/${userId}/role`, { role })
    return response.data
  },

  async deactivateUser(userId: string) {
    const response = await api.patch(`/users/${userId}/deactivate`)
    return response.data
  },

  async triggerScrape() {
    const response = await api.post("/admin/scrape/trigger")
    return response.data
  },

  async scrapeMissingPolicy() {
    const response = await api.post("/admin/scrape/missing-policy")
    return response.data
  },

  async getDataCompleteness() {
    const response = await api.get<{
      completeness_pct: number
      manifest_chapters: number
      policy_chapters: { scraped: number; target: number; missing: number }
      milvus_vectors: { laws: { count: number; target: number }; cases: { count: number; target: number } }
    }>("/admin/data-completeness")
    return response.data
  },
}
