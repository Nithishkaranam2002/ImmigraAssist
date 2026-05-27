import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { adminService } from "@/services/adminService"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Users, Loader2, ShieldCheck, UserPlus, Copy, Check } from "lucide-react"
import api from "@/services/api"

const roleColors: Record<string, any> = {
  super_admin: "default",
  admin: "default",
  attorney: "secondary",
  junior_associate: "outline",
}

const roleOptions = [
  { value: "attorney", label: "Attorney" },
  { value: "admin", label: "Admin" },
  { value: "junior_associate", label: "Junior Associate" },
]

export function UsersPage() {
  const queryClient = useQueryClient()
  const [showInviteForm, setShowInviteForm] = useState(false)
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState("attorney")
  const [inviteDesignation, setInviteDesignation] = useState("")
  const [generatedLink, setGeneratedLink] = useState("")
  const [copied, setCopied] = useState(false)
  const [inviteLoading, setInviteLoading] = useState(false)

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: adminService.listUsers,
  })

  const deactivateMutation = useMutation({
    mutationFn: adminService.deactivateUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
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
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to create invite")
    } finally {
      setInviteLoading(false)
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(generatedLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Users</h1>
          <p className="text-gray-500 text-sm mt-1">Manage firm members and their roles</p>
        </div>
        <Button onClick={() => { setShowInviteForm(!showInviteForm); setGeneratedLink("") }}>
          <UserPlus className="w-4 h-4 mr-2" />
          Invite Member
        </Button>
      </div>

      {showInviteForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Create Invite Link</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">
                  Email (optional)
                </label>
                <Input
                  placeholder="attorney@firm.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
                <p className="text-xs text-gray-400 mt-1">Leave blank to create a general invite</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {roleOptions.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Designation (optional)
              </label>
              <Input
                placeholder="e.g. Senior Immigration Attorney"
                value={inviteDesignation}
                onChange={(e) => setInviteDesignation(e.target.value)}
              />
            </div>

            {generatedLink ? (
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700">Invite link generated — valid for 7 days:</p>
                <div className="flex gap-2">
                  <Input value={generatedLink} readOnly className="bg-gray-50 text-xs" />
                  <Button variant="outline" size="icon" onClick={handleCopy}>
                    {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
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

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="w-4 h-4" /> All Users
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : users.length === 0 ? (
            <p className="text-center text-gray-400 py-8 text-sm">No users found</p>
          ) : (
            <div className="space-y-3">
              {users.map((user: any) => (
                <div key={user.id} className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
                  <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold shrink-0">
                    {user.full_name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-900">{user.full_name}</p>
                      {!user.is_active && (
                        <Badge variant="destructive" className="text-xs">Inactive</Badge>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">{user.email}</p>
                    {user.designation && (
                      <p className="text-xs text-blue-600 mt-0.5">{user.designation}</p>
                    )}
                  </div>
                  <Badge variant={roleColors[user.role] || "outline"}>
                    <ShieldCheck className="w-3 h-3 mr-1" />
                    {user.role.replace(/_/g, " ")}
                  </Badge>
                  {user.is_active && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => deactivateMutation.mutate(user.id)}
                      disabled={deactivateMutation.isPending}
                    >
                      Deactivate
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}