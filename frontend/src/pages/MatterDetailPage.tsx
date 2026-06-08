import { useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  ArrowLeft,
  Briefcase,
  Loader2,
  MessageSquare,
  Pencil,
  Save,
  X,
  Sparkles,
} from "lucide-react"
import { matterService } from "@/services/matterService"
import { platformService } from "@/services/platformService"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CaseNotesField } from "@/components/matters/CaseNotesField"
import { VisaTypeSelect } from "@/components/matters/VisaTypeSelect"
import { MATTER_QUICK_PROMPTS, matterStatusClass, matterStatusLabel } from "@/lib/matterConstants"
import { toast } from "@/hooks/useToast"

export function MatterDetailPage() {
  const { matterId } = useParams<{ matterId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState("")
  const [clientName, setClientName] = useState("")
  const [visaType, setVisaType] = useState("")
  const [description, setDescription] = useState("")
  const [status, setStatus] = useState("active")

  const { data: matter, isLoading, isError } = useQuery({
    queryKey: ["matter", matterId],
    queryFn: () => matterService.get(matterId!),
    enabled: !!matterId,
  })

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ["matter-history", matterId],
    queryFn: () => platformService.getHistory(50, matterId),
    enabled: !!matterId,
  })

  const updateMut = useMutation({
    mutationFn: (data: Parameters<typeof matterService.update>[1]) =>
      matterService.update(matterId!, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["matter", matterId] })
      qc.invalidateQueries({ queryKey: ["matters"] })
      setEditing(false)
      toast("Matter updated", "success")
    },
    onError: () => toast("Failed to update matter", "error"),
  })

  const startEdit = () => {
    if (!matter) return
    setTitle(matter.title)
    setClientName(matter.client_name || "")
    setVisaType(matter.visa_type || "")
    setDescription(matter.description || "")
    setStatus(matter.status)
    setEditing(true)
  }

  const openChat = (opts?: { prompt?: string; historyId?: string }) => {
    const params = new URLSearchParams({ matter: matterId! })
    navigate(`/chat?${params}`, {
      state: {
        prompt: opts?.prompt,
        historyId: opts?.historyId,
      },
    })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
      </div>
    )
  }

  if (isError || !matter) {
    return (
      <div className="p-6 text-center">
        <p className="text-slate-600 mb-4">Matter not found.</p>
        <Button variant="outline" onClick={() => navigate("/matters")}>
          Back to Matters
        </Button>
      </div>
    )
  }

  const missingNotes = !matter.description?.trim()

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Link to="/matters" className="hover:text-brand-600 inline-flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" /> Matters
        </Link>
      </div>

      <PageHeader
        title={matter.title}
        description={matter.client_name ? `Client: ${matter.client_name}` : "Client matter workspace"}
        action={
          <div className="flex gap-2 flex-wrap">
            {!editing ? (
              <Button variant="outline" size="sm" onClick={startEdit}>
                <Pencil className="w-4 h-4 mr-1.5" /> Edit
              </Button>
            ) : (
              <>
                <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
                  <X className="w-4 h-4 mr-1" /> Cancel
                </Button>
                <Button
                  size="sm"
                  disabled={!title.trim() || updateMut.isPending}
                  onClick={() =>
                    updateMut.mutate({
                      title: title.trim(),
                      client_name: clientName || undefined,
                      visa_type: visaType || undefined,
                      description: description || undefined,
                      status,
                    })
                  }
                >
                  {updateMut.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-1.5" /> Save
                    </>
                  )}
                </Button>
              </>
            )}
            <Button size="sm" onClick={() => openChat()}>
              <MessageSquare className="w-4 h-4 mr-1.5" /> Research this matter
            </Button>
          </div>
        }
      />

      {missingNotes && !editing && (
        <Card className="border-amber-200 bg-amber-50/50 max-w-3xl">
          <CardContent className="pt-4 pb-3 flex gap-2 text-sm text-amber-900">
            <Sparkles className="w-4 h-4 shrink-0 mt-0.5" />
            <p>
              Add <strong>case notes</strong> so the AI can personalize answers for this client
              (e.g. principal&apos;s status, in US or abroad, filing goal). One or two sentences is
              enough.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="border-slate-200 lg:col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-brand-600" />
              Matter details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {editing ? (
              <>
                <div>
                  <label className="text-xs font-medium text-slate-500">Title</label>
                  <Input value={title} onChange={(e) => setTitle(e.target.value)} className="mt-1" />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">Client name</label>
                  <Input
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">Visa type</label>
                  <div className="mt-1">
                    <VisaTypeSelect value={visaType} onChange={setVisaType} />
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">Status</label>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                    className="mt-1 w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white"
                  >
                    <option value="active">Active</option>
                    <option value="on_hold">On hold</option>
                    <option value="closed">Closed</option>
                  </select>
                </div>
                <CaseNotesField value={description} onChange={setDescription} rows={6} />
              </>
            ) : (
              <>
                {matter.client_name && (
                  <div>
                    <p className="text-xs font-medium text-slate-500">Client</p>
                    <p className="text-sm text-slate-900 mt-0.5">{matter.client_name}</p>
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  {matter.visa_type && (
                    <Badge variant="secondary">{matter.visa_type.toUpperCase()}</Badge>
                  )}
                  <Badge variant="outline" className={matterStatusClass(matter.status)}>
                    {matterStatusLabel(matter.status)}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-500">Case notes (sent to AI)</p>
                  <p className="text-sm text-slate-700 mt-1 whitespace-pre-wrap">
                    {matter.description?.trim() ||
                      "No notes yet — click Edit to add facts the AI should know about this client."}
                  </p>
                </div>
                <p className="text-xs text-slate-400">
                  Created {new Date(matter.created_at).toLocaleDateString()}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <div className="lg:col-span-2 space-y-4">
          <Card className="border-slate-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Quick research prompts</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {MATTER_QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => openChat({ prompt })}
                  className="text-left text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white hover:bg-brand-50 hover:border-brand-200 text-slate-700 transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="text-base">Research history</CardTitle>
              <span className="text-xs text-slate-500">
                {history?.length ?? 0} quer{history?.length === 1 ? "y" : "ies"} tagged to this matter
              </span>
            </CardHeader>
            <CardContent>
              {historyLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-brand-600" />
                </div>
              ) : history && history.length > 0 ? (
                <ul className="divide-y divide-slate-100">
                  {history.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        onClick={() => openChat({ historyId: item.id })}
                        className="w-full text-left py-3 first:pt-0 hover:bg-slate-50 -mx-2 px-2 rounded-lg transition-colors"
                      >
                        <p className="text-sm font-medium text-slate-900">{item.query}</p>
                        <p className="text-xs text-slate-500 mt-1 line-clamp-2">{item.answer_preview}</p>
                        <div className="flex items-center gap-2 mt-2 text-xs text-slate-400">
                          {item.visa_type && (
                            <Badge variant="outline" className="text-[10px]">
                              {item.visa_type.toUpperCase()}
                            </Badge>
                          )}
                          {item.confidence_level && <span>{item.confidence_level} confidence</span>}
                          <span>{new Date(item.created_at).toLocaleString()}</span>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-center py-10">
                  <p className="text-sm text-slate-500 mb-4">
                    No research tagged to this matter yet.
                  </p>
                  <Button onClick={() => openChat()}>
                    <MessageSquare className="w-4 h-4 mr-1.5" /> Start research
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
