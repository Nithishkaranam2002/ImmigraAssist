import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Briefcase, Plus, Trash2, Loader2 } from "lucide-react"
import { matterService } from "@/services/matterService"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { toast } from "@/hooks/useToast"

export function MattersPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState("")
  const [clientName, setClientName] = useState("")
  const [visaType, setVisaType] = useState("")

  const { data: matters, isLoading } = useQuery({
    queryKey: ["matters"],
    queryFn: matterService.list,
  })

  const createMut = useMutation({
    mutationFn: matterService.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["matters"] })
      setShowForm(false)
      setTitle("")
      setClientName("")
      setVisaType("")
      toast("Matter created", "success")
    },
    onError: () => toast("Failed to create matter", "error"),
  })

  const deleteMut = useMutation({
    mutationFn: matterService.remove,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["matters"] })
      toast("Matter deleted", "success")
    },
  })

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <PageHeader
        title="Client Matters"
        description="Organize research by client or case — tag queries to matters in chat"
        action={
          <Button size="sm" onClick={() => setShowForm((v) => !v)}>
            <Plus className="w-4 h-4 mr-1.5" /> New Matter
          </Button>
        }
      />

      {showForm && (
        <Card className="border-slate-200 max-w-lg">
          <CardContent className="pt-6 space-y-3">
            <Input placeholder="Matter title (e.g. Smith H1B)" value={title} onChange={(e) => setTitle(e.target.value)} />
            <Input placeholder="Client name" value={clientName} onChange={(e) => setClientName(e.target.value)} />
            <Input placeholder="Visa type (h1b, asylum, etc.)" value={visaType} onChange={(e) => setVisaType(e.target.value)} />
            <Button
              disabled={!title.trim() || createMut.isPending}
              onClick={() =>
                createMut.mutate({
                  title: title.trim(),
                  client_name: clientName || undefined,
                  visa_type: visaType || undefined,
                })
              }
            >
              {createMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create"}
            </Button>
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
                  <div className="flex items-center gap-2 min-w-0">
                    <Briefcase className="w-4 h-4 text-brand-600 shrink-0" />
                    <h3 className="font-semibold text-slate-900 truncate">{m.title}</h3>
                  </div>
                  <button
                    type="button"
                    onClick={() => deleteMut.mutate(m.id)}
                    className="text-slate-400 hover:text-red-500 p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                {m.client_name && <p className="text-sm text-slate-600 mt-1">{m.client_name}</p>}
                <div className="flex gap-2 mt-3">
                  {m.visa_type && <Badge variant="secondary">{m.visa_type.toUpperCase()}</Badge>}
                  <Badge variant="outline">{m.status}</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
          {matters?.length === 0 && (
            <p className="text-slate-500 text-sm col-span-full text-center py-8">
              No matters yet — create one to tag research in chat
            </p>
          )}
        </div>
      )}
    </div>
  )
}
