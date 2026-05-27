import api from "./api"
import type { Document } from "@/types"

export const documentService = {
  async upload(file: File) {
    const formData = new FormData()
    formData.append("file", file)
    const response = await api.post("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    return response.data
  },

  async list(): Promise<Document[]> {
    const response = await api.get<Document[]>("/documents/")
    return response.data
  },

  async getById(id: string): Promise<Document> {
    const response = await api.get<Document>(`/documents/${id}`)
    return response.data
  },
}
