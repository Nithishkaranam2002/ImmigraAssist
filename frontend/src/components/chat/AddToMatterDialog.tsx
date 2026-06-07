import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Loader2, Briefcase } from "lucide-react"
import { matterService } from "@/services/matterService"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
import { toast } from "@/hooks/useToast"

interface AddToMatterDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionId: string
  auditLogIds: string[]
  suggestedTitle?: string
  suggestedVisa?: string
  suggestedClient?: string
  onAttached: (matterId: string) => void
}

export function AddToMatterDialog({
  open,
  onOpenChange,
  sessionId,
  auditLogIds,
  suggestedTitle,
  suggestedVisa,
  suggestedClient,
  onAttached,
}: AddToMatterDialogProps) {
  const qc = useQueryClient()
  const [mode, setMode] = useState<"new" | "existing">("new")
  const [existingId, setExistingId] = useState("")
  const [title, setTitle] = useState("")
  const [clientName, setClientName] = useState("")
  const [visaType, setVisaType] = useState("")
  const [description, setDescription] = useState("")

  const { data: matters } = useQuery({
    queryKey: ["matters"],
    queryFn: matterService.list,
    enabled: open,
  })

  useEffect(() => {
    if (!open) return
    setMode("new")
    setTitle(suggestedTitle || "")
    setClientName(suggestedClient || "")
    setVisaType(suggestedVisa || "")
    setDescription("")
    setExistingId(matters?.[0]?.id || "")
  }, [open, suggestedTitle, suggestedVisa, suggestedClient, matters])

  const attachMut = useMutation({
    mutationFn: matterService.attachResearch,
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["matters"] })
      qc.invalidateQueries({ queryKey: ["matter-history"] })
      toast(`Saved ${result.attached_count} research item(s) to matter`, "success")
      onAttached(result.matter_id)
      onOpenChange(false)
    },
    onError: () => toast("Failed to save to matter", "error"),
  })

  const queryCount = auditLogIds.length || 1

  const handleSubmit = () => {
    if (mode === "existing") {
      if (!existingId) return
      attachMut.mutate({
        matter_id: existingId,
        audit_log_ids: auditLogIds,
        session_id: sessionId,
      })
      return
    }
    if (!title.trim()) return
    attachMut.mutate({
      title: title.trim(),
      client_name: clientName || undefined,
      visa_type: visaType || undefined,
      description: description || undefined,
      audit_log_ids: auditLogIds,
      session_id: sessionId,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-brand-600" />
            Save research to matter
          </DialogTitle>
          <DialogDescription>
            Link {queryCount} research quer{queryCount === 1 ? "y" : "ies"} from this chat to a
            client matter for organized case files.
          </DialogDescription>
        </DialogHeader>

        <div className="flex gap-2 py-2">
          <button
            type="button"
            onClick={() => setMode("new")}
            className={`flex-1 text-sm py-2 rounded-lg border transition-colors ${
              mode === "new"
                ? "border-brand-300 bg-brand-50 text-brand-800 font-medium"
                : "border-slate-200 text-slate-600 hover:bg-slate-50"
            }`}
          >
            New matter
          </button>
          <button
            type="button"
            onClick={() => setMode("existing")}
            disabled={!matters?.length}
            className={`flex-1 text-sm py-2 rounded-lg border transition-colors disabled:opacity-40 ${
              mode === "existing"
                ? "border-brand-300 bg-brand-50 text-brand-800 font-medium"
                : "border-slate-200 text-slate-600 hover:bg-slate-50"
            }`}
          >
            Existing matter
          </button>
        </div>

        {mode === "existing" ? (
          <div>
            <label className="text-xs font-medium text-slate-500">Select matter</label>
            <select
              value={existingId}
              onChange={(e) => setExistingId(e.target.value)}
              className="mt-1 w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white"
            >
              {matters?.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.title}
                  {m.client_name ? ` — ${m.client_name}` : ""}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div className="space-y-3">
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
            <CaseNotesField value={description} onChange={setDescription} rows={3} />
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={
              attachMut.isPending ||
              (mode === "new" ? !title.trim() : !existingId)
            }
            onClick={handleSubmit}
          >
            {attachMut.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              "Save to matter"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
