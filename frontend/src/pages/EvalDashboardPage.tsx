import { useQuery } from "@tanstack/react-query"
import {
  BarChart3,
  Loader2,
  ThumbsUp,
  Clock,
  MessageSquare,
  AlertTriangle,
  Activity,
  Zap,
  Database,
  Radio,
  RefreshCw,
} from "lucide-react"
import { platformService, type EvalMetrics } from "@/services/platformService"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  AreaTrend,
  DonutChart,
  HorizontalBars,
  LineTrend,
  StackedBars,
  VerticalBars,
} from "@/components/eval/SimpleCharts"

const CONFIDENCE_COLORS: Record<string, string> = {
  high: "#10b981",
  medium: "#f59e0b",
  low: "#f43f5e",
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: typeof BarChart3
  label: string
  value: string | number
  sub?: string
  accent?: string
}) {
  return (
    <Card className="border-slate-200">
      <CardContent className="pt-5 pb-5">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
            {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
          </div>
          <div
            className={cn(
              "w-10 h-10 rounded-xl flex items-center justify-center shrink-0",
              accent || "bg-brand-50"
            )}
          >
            <Icon className={cn("w-5 h-5", accent ? "text-white" : "text-brand-600")} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function formatDayLabel(iso: string) {
  const d = new Date(iso.includes("T") ? iso : `${iso}T00:00:00`)
  if (Number.isNaN(d.getTime())) return iso.slice(5)
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

function formatHourLabel(iso: string) {
  const d = new Date(iso.includes("T") ? iso : iso.replace(" ", "T"))
  if (Number.isNaN(d.getTime())) return iso.slice(11, 16)
  return d.toLocaleTimeString("en-US", { hour: "numeric" })
}

function formatTimestamp(iso: string) {
  const d = new Date(iso.replace(" ", "T"))
  if (Number.isNaN(d.getTime())) return "—"
  return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
}

function formatTime(iso?: string) {
  if (!iso) return "—"
  const d = new Date(iso.replace(" ", "T"))
  if (Number.isNaN(d.getTime())) return "—"
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit" })
}

function confidenceChartData(data: EvalMetrics) {
  return ["high", "medium", "low"]
    .filter((k) => data.confidence_distribution?.[k])
    .map((k) => ({
      label: k,
      value: data.confidence_distribution[k],
      color: CONFIDENCE_COLORS[k],
    }))
}

export function EvalDashboardPage() {
  const { data, isLoading, isError, error, refetch, dataUpdatedAt, isFetching } = useQuery({
    queryKey: ["eval-metrics"],
    queryFn: platformService.getEvalMetrics,
    refetchInterval: 15000,
    retry: 2,
  })

  const lastUpdated = data?.updated_at ? formatTime(data.updated_at) : formatTime(new Date(dataUpdatedAt).toISOString())

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-6">
        <PageHeader title="Evaluation Dashboard" description="RAG quality metrics and monitoring" />
        <div className="text-center py-16 max-w-md mx-auto">
          <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto mb-3" />
          <p className="text-slate-700 font-medium mb-1">Failed to load metrics</p>
          <p className="text-sm text-slate-500 mb-4">
            {(error as Error)?.message || "Admin access required or server unavailable."}
          </p>
          <Button onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4 mr-2" /> Retry
          </Button>
        </div>
      </div>
    )
  }

  const visaItems = Object.entries(data.visa_type_distribution || {}).map(([name, value]) => ({
    label: name,
    value,
  }))

  const modeItems = Object.entries(data.query_mode_distribution || {}).map(([mode, count]) => ({
    label: mode.replace("_", " "),
    value: count,
  }))

  const reviewItems = Object.entries(data.review_status || {}).map(([status, count]) => ({
    label: status,
    value: count,
    color: status === "pending" ? "#f59e0b" : status === "approved" ? "#10b981" : "#f43f5e",
  }))

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <PageHeader
          title="Evaluation Dashboard"
          description="Real-time RAG quality, latency, confidence, and user satisfaction"
        />
        <Badge
          variant="outline"
          className={cn(
            "text-xs gap-1.5 shrink-0",
            isFetching ? "border-brand-300 text-brand-700 bg-brand-50" : "text-slate-600"
          )}
        >
          <Radio className={cn("w-3 h-3", isFetching && "animate-pulse text-brand-600")} />
          Live · {lastUpdated}
        </Badge>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={MessageSquare}
          label="Total Queries"
          value={(data.total_queries ?? 0).toLocaleString()}
          sub={`${data.queries_today ?? 0} today · ${data.queries_last_hour ?? 0} last hour`}
        />
        <StatCard
          icon={Activity}
          label="Last 24 Hours"
          value={data.queries_last_24h ?? 0}
          sub="Rolling query volume"
          accent="bg-violet-600"
        />
        <StatCard
          icon={Clock}
          label="Avg Latency"
          value={`${((data.avg_response_time_ms ?? 0) / 1000).toFixed(1)}s`}
          sub={`p50 ${((data.latency_p50_ms ?? 0) / 1000).toFixed(1)}s · p95 ${((data.latency_p95_ms ?? 0) / 1000).toFixed(1)}s`}
        />
        <StatCard
          icon={ThumbsUp}
          label="Satisfaction"
          value={data.satisfaction_rate != null ? `${data.satisfaction_rate}%` : "—"}
          sub={`${data.feedback_positive ?? 0}↑ ${data.feedback_negative ?? 0}↓`}
          accent="bg-emerald-600"
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={BarChart3}
          label="Avg Confidence"
          value={(data.avg_confidence_score ?? 0).toFixed(2)}
          sub="0–1 retrieval + answer quality score"
        />
        <StatCard
          icon={Database}
          label="Cache Hit Rate"
          value={`${data.cache_hit_rate ?? 0}%`}
          sub={`${data.cache_hits ?? 0} cached responses`}
        />
        <StatCard
          icon={AlertTriangle}
          label="Needs Review"
          value={data.needs_review_count ?? 0}
          sub={`${data.pending_reviews ?? 0} pending in queue`}
          accent="bg-amber-500"
        />
        <StatCard
          icon={Zap}
          label="Quality Flags"
          value={data.pending_reviews ?? 0}
          sub="Awaiting attorney approval"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Query Volume — 14 Days</CardTitle>
          </CardHeader>
          <CardContent className="h-44">
            <AreaTrend
              points={(data.daily_volume ?? []).map((d) => ({
                label: formatDayLabel(d.date),
                value: d.count,
              }))}
            />
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Live Activity — Last 24 Hours</CardTitle>
          </CardHeader>
          <CardContent className="h-44">
            <LineTrend
              points={(data.hourly_activity ?? []).map((h) => ({
                label: formatHourLabel(h.hour),
                value: h.count,
              }))}
            />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Confidence Distribution</CardTitle>
          </CardHeader>
          <CardContent className="h-44">
            {confidenceChartData(data).length > 0 ? (
              <HorizontalBars items={confidenceChartData(data)} />
            ) : (
              <p className="text-xs text-slate-400 text-center py-12">No confidence data yet</p>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Top Visa Topics</CardTitle>
          </CardHeader>
          <CardContent className="h-44">
            {visaItems.length > 0 ? (
              <DonutChart items={visaItems} />
            ) : (
              <p className="text-xs text-slate-400 text-center py-12">No visa data yet</p>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Review Queue Status</CardTitle>
          </CardHeader>
          <CardContent className="h-44">
            {reviewItems.length > 0 ? (
              <VerticalBars items={reviewItems} />
            ) : (
              <p className="text-xs text-slate-400 text-center py-12">No reviews yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Feedback Trend — 7 Days</CardTitle>
          </CardHeader>
          <CardContent className="h-44">
            <StackedBars
              items={(data.feedback_trend ?? []).map((d) => ({
                label: formatDayLabel(d.date),
                positive: d.positive,
                negative: d.negative,
              }))}
            />
            <div className="flex gap-4 justify-center text-[10px] text-slate-500 mt-2">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-sm bg-emerald-500" /> Thumbs up
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-sm bg-rose-500" /> Thumbs down
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Query Modes</CardTitle>
          </CardHeader>
          <CardContent className="h-44">
            {modeItems.length > 0 ? (
              <VerticalBars items={modeItems} />
            ) : (
              <p className="text-xs text-slate-400 text-center py-12">No mode data yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Activity className="w-4 h-4 text-brand-600" />
            Recent Query Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          {(data.recent_activity ?? []).length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-6">No queries yet</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {data.recent_activity.map((item) => (
                <div key={item.id} className="py-3 flex items-start justify-between gap-4 first:pt-0 last:pb-0">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-slate-800 line-clamp-1">{item.query}</p>
                    <div className="flex flex-wrap items-center gap-2 mt-1">
                      {item.visa_type && (
                        <Badge variant="secondary" className="text-[10px]">
                          {item.visa_type.toUpperCase()}
                        </Badge>
                      )}
                      {item.confidence_level && (
                        <Badge variant="outline" className="text-[10px] capitalize">
                          {item.confidence_level}
                        </Badge>
                      )}
                      {item.from_cache && (
                        <Badge variant="outline" className="text-[10px] text-violet-600 border-violet-200">
                          cached
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs font-medium text-slate-600">
                      {((item.response_time_ms ?? 0) / 1000).toFixed(1)}s
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5">{formatTimestamp(item.created_at)}</p>
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
