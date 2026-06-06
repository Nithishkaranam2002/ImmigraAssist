import { useQuery } from "@tanstack/react-query"
import { adminService } from "@/services/adminService"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { PageHeader } from "@/components/layout/PageHeader"
import { Users, FileText, MessageSquare, ThumbsUp, Activity, Loader2 } from "lucide-react"

function StatCard({
  icon: Icon,
  value,
  label,
  iconBg,
  iconColor,
}: {
  icon: typeof Users
  value: string | number
  label: string
  iconBg: string
  iconColor: string
}) {
  return (
    <Card className="border-slate-200 shadow-sm hover:shadow-md transition-shadow">
      <CardContent className="pt-6">
        <div className="flex items-center gap-4">
          <div className={`w-11 h-11 ${iconBg} rounded-xl flex items-center justify-center shrink-0`}>
            <Icon className={`w-5 h-5 ${iconColor}`} />
          </div>
          <div>
            <p className="text-2xl font-bold text-slate-900">{value}</p>
            <p className="text-xs text-slate-500 mt-0.5">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function AdminPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: adminService.getStats,
  })

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: adminService.getHealth,
    refetchInterval: 30000,
  })

  const docCount = stats?.documents
    ? Object.values(stats.documents).reduce((a, b) => a + b, 0)
    : null

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <PageHeader
        title="Admin Dashboard"
        description="System overview, usage metrics, and service health"
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={Users}
          value={statsLoading ? "…" : (stats?.total_users ?? "—")}
          label="Total Users"
          iconBg="bg-brand-50"
          iconColor="text-brand-600"
        />
        <StatCard
          icon={FileText}
          value={statsLoading ? "…" : (stats?.total_chunks_indexed ?? "—")}
          label="Chunks Indexed"
          iconBg="bg-emerald-50"
          iconColor="text-emerald-600"
        />
        <StatCard
          icon={MessageSquare}
          value={statsLoading ? "…" : (stats?.total_queries ?? "—")}
          label="Total Queries"
          iconBg="bg-violet-50"
          iconColor="text-violet-600"
        />
        <StatCard
          icon={ThumbsUp}
          value={
            statsLoading
              ? "…"
              : stats?.feedback?.satisfaction_rate != null
                ? `${stats.feedback.satisfaction_rate}%`
                : "—"
          }
          label="Satisfaction Rate"
          iconBg="bg-amber-50"
          iconColor="text-amber-600"
        />
      </div>

      {docCount != null && (
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Document Corpus</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {Object.entries(stats?.documents ?? {}).map(([type, count]) => (
                <div
                  key={type}
                  className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 rounded-lg border border-slate-100"
                >
                  <span className="text-sm font-medium text-slate-700 capitalize">{type}</span>
                  <Badge variant="secondary">{count}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="border-slate-200 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="w-4 h-4 text-brand-600" />
            System Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          {healthLoading ? (
            <div className="flex items-center gap-2 text-slate-500 text-sm py-4">
              <Loader2 className="w-4 h-4 animate-spin" />
              Checking services...
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {health &&
                Object.entries(health)
                  .filter(([k]) => k !== "overall")
                  .map(([key, value]) => (
                    <div
                      key={key}
                      className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100"
                    >
                      <span className="text-sm font-medium text-slate-700 capitalize">
                        {key.replace(/_/g, " ")}
                      </span>
                      <Badge variant={value.includes("healthy") ? "success" : "destructive"}>
                        {value.includes("healthy") ? "Healthy" : "Down"}
                      </Badge>
                    </div>
                  ))}
              {health?.overall && (
                <div className="flex items-center justify-between p-4 bg-brand-50 rounded-xl border border-brand-100 sm:col-span-2 lg:col-span-3">
                  <span className="text-sm font-semibold text-slate-800">Overall Status</span>
                  <Badge variant={health.overall.includes("healthy") ? "success" : "destructive"}>
                    {health.overall.includes("healthy") ? "All Systems Operational" : "Issues Detected"}
                  </Badge>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
