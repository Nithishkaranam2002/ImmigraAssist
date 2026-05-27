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
}
