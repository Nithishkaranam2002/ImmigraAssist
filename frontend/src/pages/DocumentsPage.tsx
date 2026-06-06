import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Upload, FileText, Loader2, CheckCircle, XCircle, Clock, RefreshCw } from "lucide-react"
import { documentService } from "@/services/documentService"
import { adminService } from "@/services/adminService"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { PageHeader } from "@/components/layout/PageHeader"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "@/hooks/useToast"

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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
      toast("Document uploaded — ingestion started", "success")
    },
    onError: (err: any) => {
      toast(err.response?.data?.detail || "Upload failed", "error")
    },
  })

  const scrapeMutation = useMutation({
    mutationFn: () => adminService.triggerScrape(),
    onSuccess: () => toast("Scraper pipeline triggered in background", "success"),
    onError: (err: any) => toast(err.response?.data?.detail || "Scrape trigger failed", "error"),
  })

  const handleFile = (file: File) => {
    if (file.type !== "application/pdf") {
      toast("Only PDF files are accepted", "error")
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

  const completed = documents.filter((d) => d.status === "completed").length
  const processing = documents.filter((d) => d.status === "processing" || d.status === "pending").length

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <PageHeader
        title="Documents"
        description="Upload USCIS policy PDFs and manage the knowledge base corpus"
        action={
          <Button
            variant="outline"
            size="sm"
            onClick={() => scrapeMutation.mutate()}
            disabled={scrapeMutation.isPending}
          >
            {scrapeMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Re-scrape Sources
          </Button>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="pt-5 pb-4">
            <p className="text-2xl font-bold text-slate-900">{documents.length}</p>
            <p className="text-xs text-slate-500 mt-0.5">Total Documents</p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="pt-5 pb-4">
            <p className="text-2xl font-bold text-emerald-600">{completed}</p>
            <p className="text-xs text-slate-500 mt-0.5">Indexed</p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="pt-5 pb-4">
            <p className="text-2xl font-bold text-amber-600">{processing}</p>
            <p className="text-xs text-slate-500 mt-0.5">In Progress</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-200 shadow-sm">
        <CardContent className="pt-6">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
              dragOver ? "border-brand-400 bg-brand-50" : "border-slate-200 hover:border-slate-300"
            }`}
          >
            {uploadMutation.isPending ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-10 h-10 text-brand-500 animate-spin" />
                <p className="text-sm text-slate-600">Uploading and starting ingestion...</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <Upload className="w-10 h-10 text-slate-400" />
                <p className="text-sm font-medium text-slate-700">Drop PDF here or click to upload</p>
                <p className="text-xs text-slate-400">USCIS policy docs or case files · Max 50MB</p>
                <label>
                  <input
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                  />
                  <Button variant="outline" size="sm" type="button">
                    Browse Files
                  </Button>
                </label>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="border-slate-200 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="w-4 h-4" /> Uploaded Documents
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : documents.length === 0 ? (
            <p className="text-center text-slate-400 py-8 text-sm">No documents uploaded yet</p>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => {
                const config = statusConfig[doc.status] || statusConfig.pending
                const StatusIcon = config.icon
                return (
                  <div key={doc.id} className="flex items-center gap-4 p-4 bg-slate-50 rounded-xl border border-slate-100">
                    <FileText className="w-8 h-8 text-slate-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">{doc.filename}</p>
                      <p className="text-xs text-slate-500">
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
