import api from "./api"

export interface Matter {
  id: string
  title: string
  client_name: string | null
  visa_type: string | null
  description: string | null
  status: string
  created_at: string
  query_count?: number
}

export const matterService = {
  async list(): Promise<Matter[]> {
    const res = await api.get<Matter[]>("/matters/")
    return res.data
  },

  async get(id: string): Promise<Matter> {
    const res = await api.get<Matter>(`/matters/${id}`)
    return res.data
  },

  async create(data: {
    title: string
    client_name?: string
    visa_type?: string
    description?: string
  }): Promise<{ id: string; title: string }> {
    const res = await api.post("/matters/", data)
    return res.data
  },

  async update(
    id: string,
    data: Partial<{ title: string; client_name: string; visa_type: string; description: string; status: string }>
  ) {
    const res = await api.patch(`/matters/${id}`, data)
    return res.data
  },

  async remove(id: string) {
    await api.delete(`/matters/${id}`)
  },

  async attachResearch(data: {
    matter_id?: string
    title?: string
    client_name?: string
    visa_type?: string
    description?: string
    audit_log_ids: string[]
    session_id: string
  }): Promise<{ matter_id: string; title: string; attached_count: number }> {
    const res = await api.post("/matters/attach-research", data)
    return res.data
  },
}
