import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Briefcase, Plus, Trash2, Loader2, MessageSquare, ChevronRight, Sparkles } from "lucide-react"
import { matterService } from "@/services/matterService"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { CaseNotesField } from "@/components/matters/CaseNotesField"
import { VisaTypeSelect } from "@/components/matters/VisaTypeSelect"
import { matterStatusClass, matterStatusLabel } from "@/lib/matterConstants"
import { toast } from "@/hooks/useToast"

export function MattersPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState("")
  const [clientName, setClientName] = useState("")
  const [visaType, setVisaType] = useState("")
  const [description, setDescription] = useState("")
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteTitle, setDeleteTitle] = useState("")

  const { data: matters, isLoading } = useQuery({
    queryKey: ["matters"],
    queryFn: matterService.list,
  })

  const createMut = useMutation({
    mutationFn: matterService.create,
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["matters"] })
      setShowForm(false)
      setTitle("")
      setClientName("")
      setVisaType("")
      setDescription("")
      toast("Matter created", "success")
      navigate(`/matters/${created.id}`)
    },
    onError: () => toast("Failed to create matter", "error"),
  })

  const deleteMut = useMutation({
    mutationFn: matterService.remove,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["matters"] })
      setDeleteId(null)
      toast("Matter deleted", "success")
    },
    onError: () => toast("Failed to delete matter", "error"),
  })

  const confirmDelete = (id: string, matterTitle: string) => {
    setDeleteId(id)
    setDeleteTitle(matterTitle)
  }

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <PageHeader
        title="Client Matters"
        description="One workspace per client or case — case notes personalize AI research in chat"
        action={
          <Button size="sm" onClick={() => setShowForm((v) => !v)}>
            <Plus className="w-4 h-4 mr-1.5" /> New Matter
          </Button>
        }
      />

      <Card className="border-brand-100 bg-brand-50/40 max-w-3xl">
        <CardContent className="pt-5 pb-4 flex gap-3">
          <Sparkles className="w-5 h-5 text-brand-600 shrink-0 mt-0.5" />
          <div className="text-sm text-brand-900">
            <p className="font-medium">How matters work</p>
            <p className="text-brand-800/80 mt-1 text-xs leading-relaxed">
              Add a short case description, click <strong>Research</strong>, and ask questions like
              &quot;What documents does this client need?&quot; — the AI uses your notes plus USCIS
              policy sources. Research is saved under this matter.
            </p>
          </div>
        </CardContent>
      </Card>

      {showForm && (
        <Card className="border-slate-200 max-w-2xl">
          <CardContent className="pt-6 space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-500">Matter title *</label>
              <Input
                className="mt-1"
                placeholder="e.g. Garcia H-4 EAD"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-slate-500">Client name</label>
                <Input
                  className="mt-1"
                  placeholder="Maria Garcia"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500">Visa type</label>
                <div className="mt-1">
                  <VisaTypeSelect value={visaType} onChange={setVisaType} />
                </div>
              </div>
            </div>
            <CaseNotesField value={description} onChange={setDescription} />
            <div className="flex gap-2">
              <Button
                disabled={!title.trim() || createMut.isPending}
                onClick={() =>
                  createMut.mutate({
                    title: title.trim(),
                    client_name: clientName || undefined,
                    visa_type: visaType || undefined,
                    description: description || undefined,
                  })
                }
              >
                {createMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create matter"}
              </Button>
              <Button variant="ghost" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {matters?.map((m) => (
            <Card key={m.id} className="border-slate-200 hover:shadow-md transition-shadow">
              <CardContent className="pt-5">
                <div className="flex items-start justify-between gap-2">
                  <Link
                    to={`/matters/${m.id}`}
                    className="flex items-center gap-2 min-w-0 group"
                  >
                    <Briefcase className="w-4 h-4 text-brand-600 shrink-0" />
                    <h3 className="font-semibold text-slate-900 truncate group-hover:text-brand-700">
                      {m.title}
                    </h3>
                  </Link>
                  <button
                    type="button"
                    onClick={() => confirmDelete(m.id, m.title)}
                    className="text-slate-400 hover:text-red-500 p-1 shrink-0"
                    aria-label={`Delete ${m.title}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                {m.client_name && <p className="text-sm text-slate-600 mt-1">{m.client_name}</p>}
                {m.description ? (
                  <p className="text-xs text-slate-500 mt-2 line-clamp-2">{m.description}</p>
                ) : (
                  <p className="text-xs text-amber-600/90 mt-2">Add case notes for personalized AI answers</p>
                )}
                <div className="flex flex-wrap gap-2 mt-3">
                  {m.visa_type && <Badge variant="secondary">{m.visa_type.toUpperCase()}</Badge>}
                  <Badge variant="outline" className={matterStatusClass(m.status)}>
                    {matterStatusLabel(m.status)}
                  </Badge>
                  {(m.query_count ?? 0) > 0 && (
                    <Badge variant="outline" className="text-slate-600">
                      {m.query_count} research
                    </Badge>
                  )}
                </div>
                <div className="flex gap-2 mt-4">
                  <Button
                    size="sm"
                    className="flex-1"
                    onClick={() => navigate(`/chat?matter=${m.id}`)}
                  >
                    <MessageSquare className="w-3.5 h-3.5 mr-1" /> Research
                  </Button>
                  <Link
                    to={`/matters/${m.id}`}
                    className="inline-flex items-center justify-center h-9 rounded-md px-3 border border-gray-300 bg-white hover:bg-gray-50 text-gray-700"
                    title="View matter"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
          {matters?.length === 0 && (
            <Card className="col-span-full border-dashed border-slate-200">
              <CardContent className="py-12 text-center">
                <Briefcase className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                <p className="text-slate-600 font-medium">No matters yet</p>
                <p className="text-slate-500 text-sm mt-1 max-w-md mx-auto">
                  Create a matter for each client case. A few lines of case notes are enough for
                  tailored research memos.
                </p>
                <Button className="mt-4" size="sm" onClick={() => setShowForm(true)}>
                  <Plus className="w-4 h-4 mr-1" /> Create your first matter
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      <Dialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete matter?</DialogTitle>
            <DialogDescription>
              Delete <strong>{deleteTitle}</strong>? Research history stays in audit logs but will
              no longer be grouped under this matter.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setDeleteId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deleteMut.isPending}
              onClick={() => deleteId && deleteMut.mutate(deleteId)}
            >
              {deleteMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
