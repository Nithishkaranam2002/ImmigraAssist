import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Upload, FileText, Loader2, CheckCircle, XCircle, Clock } from "lucide-react"
import { documentService } from "@/services/documentService"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

const statusConfig = {
  completed: { icon: CheckCircle, color: "success", label: "Completed" },
  processing: { icon: Loader2, color: "warning", label: "Processing" },
  pending: { icon: Clock, color: "secondary", label: "Pending" },
  failed: { icon: XCircle, color: "destructive", label: "Failed" },
} as const

export function DocumentsPage() {
  const [dragOver, setDragOver] = useState(false)
  const queryClient = useQueryClient()

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: documentService.list,
    refetchInterval: 5000,
  })

  const uploadMutation = useMutation({
    mutationFn: documentService.upload,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  })

  const handleFile = (file: File) => {
    if (file.type !== "application/pdf") {
      alert("Only PDF files are accepted")
      return
    }
    uploadMutation.mutate(file)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
        <p className="text-gray-500 text-sm mt-1">Upload USCIS policy PDFs and case files</p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
              dragOver ? "border-blue-400 bg-blue-50" : "border-gray-300 hover:border-gray-400"
            }`}
          >
            {uploadMutation.isPending ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
                <p className="text-sm text-gray-600">Uploading and starting ingestion...</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <Upload className="w-10 h-10 text-gray-400" />
                <p className="text-sm font-medium text-gray-700">Drop PDF here or click to upload</p>
                <p className="text-xs text-gray-400">USCIS policy docs or case files · Max 50MB</p>
                <label>
                  <input
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                  />
                  <Button variant="outline" size="sm">
                    <span>Browse Files</span>
                  </Button>
                </label>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-4 h-4" /> Uploaded Documents
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : documents.length === 0 ? (
            <p className="text-center text-gray-400 py-8 text-sm">No documents uploaded yet</p>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => {
                const config = statusConfig[doc.status] || statusConfig.pending
                const StatusIcon = config.icon
                return (
                  <div key={doc.id} className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
                    <FileText className="w-8 h-8 text-gray-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{doc.filename}</p>
                      <p className="text-xs text-gray-500">
                        v{doc.version} · {doc.total_chunks} chunks
                        {doc.visa_type && ` · ${doc.visa_type.toUpperCase()}`}
                      </p>
                    </div>
                    <Badge variant={doc.doc_type === "law" ? "default" : "secondary"}>
                      {doc.doc_type}
                    </Badge>
                    <Badge variant={config.color as any} className="flex items-center gap-1">
                      <StatusIcon className={`w-3 h-3 ${doc.status === "processing" ? "animate-spin" : ""}`} />
                      {config.label}
                    </Badge>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
