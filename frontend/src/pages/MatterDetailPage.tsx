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
} from "lucide-react"
import { matterService } from "@/services/matterService"
import { platformService } from "@/services/platformService"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
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

  const openChat = () => {
    navigate(`/chat?matter=${matterId}`)
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
          <div className="flex gap-2">
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
            <Button size="sm" onClick={openChat}>
              <MessageSquare className="w-4 h-4 mr-1.5" /> Research this matter
            </Button>
          </div>
        }
      />

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
                  <Input
                    value={visaType}
                    onChange={(e) => setVisaType(e.target.value)}
                    placeholder="h1b, h4, asylum..."
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">Status</label>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                    className="mt-1 w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white"
                  >
                    <option value="active">active</option>
                    <option value="on_hold">on_hold</option>
                    <option value="closed">closed</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">Case description</label>
                  <Textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Facts, deadlines, strategy notes for this case..."
                    className="mt-1 min-h-[140px]"
                    rows={6}
                  />
                </div>
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
                  <Badge variant="outline">{matter.status}</Badge>
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-500">Case description</p>
                  <p className="text-sm text-slate-700 mt-1 whitespace-pre-wrap">
                    {matter.description?.trim() || "No description yet — add case notes when you edit this matter."}
                  </p>
                </div>
                <p className="text-xs text-slate-400">
                  Created {new Date(matter.created_at).toLocaleDateString()}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200 lg:col-span-2">
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
                  <li key={item.id} className="py-3 first:pt-0">
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
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-center py-10">
                <p className="text-sm text-slate-500 mb-4">
                  No research tagged to this matter yet.
                </p>
                <Button onClick={openChat}>
                  <MessageSquare className="w-4 h-4 mr-1.5" /> Start research
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
