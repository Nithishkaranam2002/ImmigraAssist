import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { adminService } from "@/services/adminService"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { PageHeader } from "@/components/layout/PageHeader"
import { Skeleton } from "@/components/ui/skeleton"
import { BarChart3, Search, Clock } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

export function AuditPage() {
  const [search, setSearch] = useState("")

  const { data: logs = [], isLoading } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: adminService.getAuditLogs,
    refetchInterval: 10000,
  })

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    if (!q) return logs
    return logs.filter((log) => log.query.toLowerCase().includes(q))
  }, [logs, search])

  const avgMs = logs.length
    ? Math.round(logs.reduce((s, l) => s + l.response_time_ms, 0) / logs.length)
    : 0

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <PageHeader
        title="Audit Logs"
        description="Complete query history with response metrics for compliance review"
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="pt-5 pb-4">
            <p className="text-2xl font-bold text-slate-900">{logs.length}</p>
            <p className="text-xs text-slate-500 mt-0.5">Total Queries</p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="pt-5 pb-4">
            <p className="text-2xl font-bold text-brand-600">{avgMs}ms</p>
            <p className="text-xs text-slate-500 mt-0.5">Avg Response Time</p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="pt-5 pb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-slate-400" />
            <div>
              <p className="text-sm font-medium text-slate-700">Auto-refreshes</p>
              <p className="text-xs text-slate-500">Every 10 seconds</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <Input
          placeholder="Search queries..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      <Card className="border-slate-200 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart3 className="w-4 h-4" /> Recent Queries
            {search && <Badge variant="secondary">{filtered.length} results</Badge>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-20 w-full" />)}
            </div>
          ) : filtered.length === 0 ? (
            <p className="text-center text-slate-400 py-8 text-sm">
              {search ? "No queries match your search" : "No queries yet"}
            </p>
          ) : (
            <div className="space-y-2">
              {filtered.map((log) => (
                <div key={log.id} className="p-4 bg-slate-50 rounded-xl border border-slate-100 space-y-2">
                  <div className="flex items-start justify-between gap-4">
                    <p className="text-sm text-slate-800 flex-1 leading-relaxed">{log.query}</p>
                    {log.visa_type_detected && (
                      <Badge variant="secondary" className="shrink-0">
                        {log.visa_type_detected.toUpperCase()}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap">
                    <span>{(log.response_time_ms / 1000).toFixed(1)}s</span>
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
