import { useQuery } from "@tanstack/react-query"
import { format, parseISO } from "date-fns"
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
} from "lucide-react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { platformService, type EvalMetrics } from "@/services/platformService"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const CHART_COLORS = {
  brand: "#4f46e5",
  brandLight: "#818cf8",
  emerald: "#10b981",
  amber: "#f59e0b",
  rose: "#f43f5e",
  slate: "#94a3b8",
}

const CONFIDENCE_COLORS: Record<string, string> = {
  high: CHART_COLORS.emerald,
  medium: CHART_COLORS.amber,
  low: CHART_COLORS.rose,
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

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: { value: number; name: string; color: string }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      {label && <p className="font-medium text-slate-700 mb-1">{label}</p>}
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <span className="font-semibold">{p.value}</span>
        </p>
      ))}
    </div>
  )
}

function formatHourLabel(iso: string) {
  try {
    return format(parseISO(iso), "ha")
  } catch {
    return iso.slice(11, 16)
  }
}

function formatDayLabel(iso: string) {
  try {
    return format(parseISO(iso), "MMM d")
  } catch {
    return iso.slice(5)
  }
}

function confidenceChartData(data: EvalMetrics) {
  const order = ["high", "medium", "low"]
  return order
    .filter((k) => data.confidence_distribution[k])
    .map((k) => ({
      level: k.charAt(0).toUpperCase() + k.slice(1),
      count: data.confidence_distribution[k],
      fill: CONFIDENCE_COLORS[k] || CHART_COLORS.slate,
    }))
}

function visaChartData(data: EvalMetrics) {
  return Object.entries(data.visa_type_distribution).map(([name, value]) => ({
    name,
    value,
  }))
}

function modeChartData(data: EvalMetrics) {
  return Object.entries(data.query_mode_distribution).map(([mode, count]) => ({
    mode: mode.replace("_", " "),
    count,
  }))
}

function reviewChartData(data: EvalMetrics) {
  const colors: Record<string, string> = {
    pending: CHART_COLORS.amber,
    approved: CHART_COLORS.emerald,
    rejected: CHART_COLORS.rose,
  }
  return Object.entries(data.review_status).map(([status, count]) => ({
    status: status.charAt(0).toUpperCase() + status.slice(1),
    count,
    fill: colors[status] || CHART_COLORS.slate,
  }))
}

export function EvalDashboardPage() {
  const { data, isLoading, dataUpdatedAt, isFetching } = useQuery({
    queryKey: ["eval-metrics"],
    queryFn: platformService.getEvalMetrics,
    refetchInterval: 15000,
  })

  const lastUpdated = data?.updated_at
    ? format(parseISO(data.updated_at), "h:mm:ss a")
    : dataUpdatedAt
      ? format(dataUpdatedAt, "h:mm:ss a")
      : "—"

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <PageHeader
          title="Evaluation Dashboard"
          description="Real-time RAG quality, latency, confidence, and user satisfaction"
        />
        <div className="flex items-center gap-2 shrink-0">
          <Badge
            variant="outline"
            className={cn(
              "text-xs gap-1.5",
              isFetching ? "border-brand-300 text-brand-700 bg-brand-50" : "text-slate-600"
            )}
          >
            <Radio className={cn("w-3 h-3", isFetching && "animate-pulse text-brand-600")} />
            Live · {lastUpdated}
          </Badge>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
        </div>
      ) : data ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              icon={MessageSquare}
              label="Total Queries"
              value={data.total_queries.toLocaleString()}
              sub={`${data.queries_today} today · ${data.queries_last_hour} last hour`}
            />
            <StatCard
              icon={Activity}
              label="Last 24 Hours"
              value={data.queries_last_24h}
              sub="Rolling query volume"
              accent="bg-violet-600"
            />
            <StatCard
              icon={Clock}
              label="Avg Latency"
              value={`${(data.avg_response_time_ms / 1000).toFixed(1)}s`}
              sub={`p50 ${(data.latency_p50_ms / 1000).toFixed(1)}s · p95 ${(data.latency_p95_ms / 1000).toFixed(1)}s`}
            />
            <StatCard
              icon={ThumbsUp}
              label="Satisfaction"
              value={data.satisfaction_rate != null ? `${data.satisfaction_rate}%` : "—"}
              sub={`${data.feedback_positive}↑ ${data.feedback_negative}↓`}
              accent="bg-emerald-600"
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              icon={BarChart3}
              label="Avg Confidence"
              value={data.avg_confidence_score.toFixed(2)}
              sub="0–1 retrieval + answer quality score"
            />
            <StatCard
              icon={Database}
              label="Cache Hit Rate"
              value={`${data.cache_hit_rate}%`}
              sub={`${data.cache_hits} cached responses`}
            />
            <StatCard
              icon={AlertTriangle}
              label="Needs Review"
              value={data.needs_review_count}
              sub={`${data.pending_reviews} pending in queue`}
              accent="bg-amber-500"
            />
            <StatCard
              icon={Zap}
              label="Quality Flags"
              value={data.pending_reviews}
              sub="Awaiting attorney approval"
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Query Volume — 14 Days</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.daily_volume}>
                      <defs>
                        <linearGradient id="volumeGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={CHART_COLORS.brand} stopOpacity={0.25} />
                          <stop offset="95%" stopColor={CHART_COLORS.brand} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="date"
                        tickFormatter={formatDayLabel}
                        tick={{ fontSize: 11, fill: "#64748b" }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                      <Tooltip content={<ChartTooltip />} />
                      <Area
                        type="monotone"
                        dataKey="count"
                        name="Queries"
                        stroke={CHART_COLORS.brand}
                        fill="url(#volumeGrad)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Live Activity — Last 24 Hours</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.hourly_activity}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="hour"
                        tickFormatter={formatHourLabel}
                        tick={{ fontSize: 10, fill: "#64748b" }}
                        axisLine={false}
                        tickLine={false}
                        interval={3}
                      />
                      <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                      <Tooltip
                        content={<ChartTooltip />}
                        labelFormatter={(v) => formatHourLabel(String(v))}
                      />
                      <Line
                        type="monotone"
                        dataKey="count"
                        name="Queries"
                        stroke={CHART_COLORS.emerald}
                        strokeWidth={2}
                        dot={{ r: 2, fill: CHART_COLORS.emerald }}
                        activeDot={{ r: 4 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Confidence Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-52">
                  {confidenceChartData(data).length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={confidenceChartData(data)} layout="vertical" margin={{ left: 8 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                        <XAxis type="number" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                        <YAxis
                          type="category"
                          dataKey="level"
                          tick={{ fontSize: 11, fill: "#64748b" }}
                          axisLine={false}
                          tickLine={false}
                          width={56}
                        />
                        <Tooltip content={<ChartTooltip />} />
                        <Bar dataKey="count" name="Answers" radius={[0, 4, 4, 0]}>
                          {confidenceChartData(data).map((entry) => (
                            <Cell key={entry.level} fill={entry.fill} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-xs text-slate-400 text-center py-16">No confidence data yet</p>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Top Visa Topics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-52">
                  {visaChartData(data).length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={visaChartData(data)}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          innerRadius={45}
                          outerRadius={72}
                          paddingAngle={2}
                        >
                          {visaChartData(data).map((_, i) => (
                            <Cell
                              key={i}
                              fill={
                                [CHART_COLORS.brand, CHART_COLORS.brandLight, CHART_COLORS.emerald, CHART_COLORS.amber, CHART_COLORS.rose, CHART_COLORS.slate][
                                  i % 6
                                ]
                              }
                            />
                          ))}
                        </Pie>
                        <Tooltip content={<ChartTooltip />} />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-xs text-slate-400 text-center py-16">No visa data yet</p>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Review Queue Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-52">
                  {reviewChartData(data).length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={reviewChartData(data)}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="status" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                        <Tooltip content={<ChartTooltip />} />
                        <Bar dataKey="count" name="Items" radius={[4, 4, 0, 0]}>
                          {reviewChartData(data).map((entry) => (
                            <Cell key={entry.status} fill={entry.fill} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-xs text-slate-400 text-center py-16">No reviews yet</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Feedback Trend — 7 Days</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-52">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.feedback_trend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="date"
                        tickFormatter={formatDayLabel}
                        tick={{ fontSize: 11, fill: "#64748b" }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                      <Tooltip
                        content={<ChartTooltip />}
                        labelFormatter={(v) => formatDayLabel(String(v))}
                      />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey="positive" name="Thumbs up" fill={CHART_COLORS.emerald} radius={[4, 4, 0, 0]} />
                      <Bar dataKey="negative" name="Thumbs down" fill={CHART_COLORS.rose} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Query Modes</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-52">
                  {modeChartData(data).length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={modeChartData(data)}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="mode" tick={{ fontSize: 10, fill: "#64748b" }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                        <Tooltip content={<ChartTooltip />} />
                        <Bar dataKey="count" name="Queries" fill={CHART_COLORS.brand} radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-xs text-slate-400 text-center py-16">No mode data yet</p>
                  )}
                </div>
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
              {data.recent_activity.length === 0 ? (
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
                          {(item.response_time_ms / 1000).toFixed(1)}s
                        </p>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {format(parseISO(item.created_at), "MMM d, h:mm a")}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  )
}
