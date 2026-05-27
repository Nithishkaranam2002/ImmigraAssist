import { useQuery } from "@tanstack/react-query"
import { adminService } from "@/services/adminService"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BarChart3, Loader2 } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

export function AuditPage() {
  const { data: logs = [], isLoading } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: adminService.getAuditLogs,
    refetchInterval: 10000,
  })

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>
        <p className="text-gray-500 text-sm mt-1">All queries made by users</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" /> Recent Queries
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : logs.length === 0 ? (
            <p className="text-center text-gray-400 py-8 text-sm">No queries yet</p>
          ) : (
            <div className="space-y-3">
              {logs.map((log) => (
                <div key={log.id} className="p-4 bg-gray-50 rounded-lg space-y-2">
                  <div className="flex items-start justify-between gap-4">
                    <p className="text-sm text-gray-800 flex-1">{log.query}</p>
                    <div className="flex items-center gap-2 shrink-0">
                      {log.visa_type_detected && (
                        <Badge variant="secondary">{log.visa_type_detected.toUpperCase()}</Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-400">
                    <span>{log.response_time_ms}ms</span>
                    <span>{log.token_count} tokens</span>
                    <span>{formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
