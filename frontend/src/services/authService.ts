import api from "./api"
import type { AuthResponse, LoginRequest } from "@/types"

interface RegisterRequest {
  full_name: string
  email: string
  password: string
  role?: string
  designation?: string
  invite_token?: string
}

export const authService = {
  async login(data: LoginRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>("/auth/login", data)
    return response.data
  },

  async register(data: RegisterRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>("/auth/register", data)
    return response.data
  },

  async getMe() {
    const response = await api.get("/users/me")
    return response.data
  },

  logout() {
    localStorage.removeItem("access_token")
    localStorage.removeItem("user")
  },
}