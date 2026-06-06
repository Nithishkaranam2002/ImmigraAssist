import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { adminService } from "@/services/adminService"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PageHeader } from "@/components/layout/PageHeader"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Users, Loader2, ShieldCheck, UserPlus, Copy, Check } from "lucide-react"
import { toast } from "@/hooks/useToast"
import api from "@/services/api"
import type { UserRole } from "@/types"

const roleColors: Record<string, "default" | "secondary" | "outline"> = {
  super_admin: "default",
  admin: "default",
  attorney: "secondary",
  junior_associate: "outline",
}

const roleOptions: { value: UserRole; label: string }[] = [
  { value: "junior_associate", label: "Junior Associate" },
  { value: "attorney", label: "Attorney" },
  { value: "admin", label: "Admin" },
]

export function UsersPage() {
  const queryClient = useQueryClient()
  const [showInviteForm, setShowInviteForm] = useState(false)
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState<UserRole>("attorney")
  const [inviteDesignation, setInviteDesignation] = useState("")
  const [generatedLink, setGeneratedLink] = useState("")
  const [copied, setCopied] = useState(false)
  const [inviteLoading, setInviteLoading] = useState(false)
  const [deactivateTarget, setDeactivateTarget] = useState<{ id: string; name: string } | null>(null)

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: adminService.listUsers,
  })

  const deactivateMutation = useMutation({
    mutationFn: adminService.deactivateUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      setDeactivateTarget(null)
      toast("User deactivated", "success")
    },
    onError: (err: any) => toast(err.response?.data?.detail || "Failed to deactivate", "error"),
  })

  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) => adminService.updateUserRole(id, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      toast("Role updated", "success")
    },
    onError: (err: any) => toast(err.response?.data?.detail || "Failed to update role", "error"),
  })

  const handleCreateInvite = async () => {
    setInviteLoading(true)
    try {
      const response = await api.post("/invites/", {
        email: inviteEmail || null,
        role: inviteRole,
        designation: inviteDesignation || null,
      })
      const rawLink = response.data.invite_link
      const token = new URL(rawLink).searchParams.get("token")
      setGeneratedLink(`${window.location.origin}/signup?token=${token}`)
      toast("Invite link generated", "success")
    } catch (err: any) {
      toast(err.response?.data?.detail || "Failed to create invite", "error")
    } finally {
      setInviteLoading(false)
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(generatedLink)
    setCopied(true)
    toast("Link copied to clipboard", "info")
    setTimeout(() => setCopied(false), 2000)
  }

  const activeCount = users.filter((u: any) => u.is_active).length

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <PageHeader
        title="Team"
        description={`${activeCount} active member${activeCount !== 1 ? "s" : ""} · Manage roles and invites`}
        action={
          <Button size="sm" onClick={() => { setShowInviteForm(!showInviteForm); setGeneratedLink("") }}>
            <UserPlus className="w-4 h-4 mr-2" />
            Invite Member
          </Button>
        }
      />

      {showInviteForm && (
        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Create Invite Link</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-slate-700 block mb-1.5">Email (optional)</label>
                <Input
                  placeholder="attorney@firm.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
                <p className="text-xs text-slate-400 mt-1">Leave blank for a general invite</p>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700 block mb-1.5">Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as UserRole)}
                  className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  {roleOptions.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1.5">Designation (optional)</label>
              <Input
                placeholder="e.g. Senior Immigration Attorney"
                value={inviteDesignation}
                onChange={(e) => setInviteDesignation(e.target.value)}
              />
            </div>

            {generatedLink ? (
              <div className="space-y-2">
                <p className="text-sm font-medium text-slate-700">Invite link — valid for 7 days:</p>
                <div className="flex gap-2">
                  <Input value={generatedLink} readOnly className="bg-slate-50 text-xs" />
                  <Button variant="outline" size="icon" onClick={handleCopy}>
                    {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
                <Button variant="outline" size="sm" onClick={() => { setGeneratedLink(""); setInviteEmail(""); setInviteDesignation("") }}>
                  Create another
                </Button>
              </div>
            ) : (
              <Button onClick={handleCreateInvite} disabled={inviteLoading}>
                {inviteLoading ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Generating...</> : "Generate Invite Link"}
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      <Card className="border-slate-200 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="w-4 h-4" /> All Users
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
            </div>
          ) : users.length === 0 ? (
            <p className="text-center text-slate-400 py-8 text-sm">No users found</p>
          ) : (
            <div className="space-y-2">
              {users.map((user: any) => (
                <div key={user.id} className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 bg-slate-50 rounded-xl border border-slate-100">
                  <div className="w-10 h-10 rounded-full bg-brand-600 flex items-center justify-center text-white font-bold shrink-0">
                    {user.full_name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-medium text-slate-900">{user.full_name}</p>
                      {!user.is_active && <Badge variant="destructive" className="text-xs">Inactive</Badge>}
                    </div>
                    <p className="text-xs text-slate-500">{user.email}</p>
                    {user.designation && <p className="text-xs text-brand-600 mt-0.5">{user.designation}</p>}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {user.role !== "super_admin" && user.is_active ? (
                      <select
                        value={user.role}
                        onChange={(e) => roleMutation.mutate({ id: user.id, role: e.target.value })}
                        disabled={roleMutation.isPending}
                        className="h-9 rounded-md border border-slate-200 bg-white px-2 text-xs capitalize"
                      >
                        {roleOptions.map((r) => (
                          <option key={r.value} value={r.value}>{r.label}</option>
                        ))}
                      </select>
                    ) : (
                      <Badge variant={roleColors[user.role] || "outline"}>
                        <ShieldCheck className="w-3 h-3 mr-1" />
                        {user.role.replace(/_/g, " ")}
                      </Badge>
                    )}
                    {user.is_active && user.role !== "super_admin" && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setDeactivateTarget({ id: user.id, name: user.full_name })}
                      >
                        Deactivate
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!deactivateTarget} onOpenChange={() => setDeactivateTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Deactivate user?</DialogTitle>
            <DialogDescription>
              {deactivateTarget?.name} will lose access immediately. This can be reversed by an admin.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeactivateTarget(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => deactivateTarget && deactivateMutation.mutate(deactivateTarget.id)}
              disabled={deactivateMutation.isPending}
            >
              {deactivateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Deactivate"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
