import { useQuery } from "@tanstack/react-query"
import { BarChart3, Loader2, ThumbsUp, Clock, MessageSquare, AlertTriangle } from "lucide-react"
import { platformService } from "@/services/platformService"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function Stat({ icon: Icon, label, value, sub }: {
  icon: typeof BarChart3
  label: string
  value: string | number
  sub?: string
}) {
  return (
    <Card className="border-slate-200">
      <CardContent className="pt-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center">
            <Icon className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-slate-900">{value}</p>
            <p className="text-xs text-slate-500">{label}</p>
            {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function EvalDashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["eval-metrics"],
    queryFn: platformService.getEvalMetrics,
    refetchInterval: 60000,
  })

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <PageHeader
        title="Evaluation Dashboard"
        description="RAG quality metrics, latency, and user satisfaction"
      />

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
        </div>
      ) : data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Stat icon={MessageSquare} label="Total Queries" value={data.total_queries} />
            <Stat
              icon={Clock}
              label="Avg Response Time"
              value={`${(data.avg_response_time_ms / 1000).toFixed(1)}s`}
            />
            <Stat
              icon={ThumbsUp}
              label="Satisfaction Rate"
              value={data.satisfaction_rate != null ? `${data.satisfaction_rate}%` : "—"}
              sub={`${data.feedback_positive}↑ ${data.feedback_negative}↓`}
            />
            <Stat
              icon={BarChart3}
              label="RAGAS Score"
              value={data.ragas_score.toFixed(3)}
              sub="Faithfulness benchmark"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="text-sm">Confidence Distribution</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {Object.entries(data.confidence_distribution).map(([level, count]) => (
                  <div key={level} className="flex justify-between text-sm">
                    <span className="capitalize text-slate-600">{level}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
                {Object.keys(data.confidence_distribution).length === 0 && (
                  <p className="text-xs text-slate-400">No data yet</p>
                )}
              </CardContent>
            </Card>

            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  Pending Reviews
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-slate-900">{data.pending_reviews}</p>
                <p className="text-xs text-slate-500 mt-1">Low-confidence answers awaiting review</p>
              </CardContent>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  )
}
