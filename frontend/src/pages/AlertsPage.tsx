import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Bell, ExternalLink, Loader2 } from "lucide-react"
import { platformService } from "@/services/platformService"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

export function AlertsPage() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ["policy-alerts"],
    queryFn: platformService.listAlerts,
    refetchInterval: 120000,
  })

  const readMut = useMutation({
    mutationFn: platformService.markAlertRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["policy-alerts"] }),
  })

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <PageHeader
        title="Policy Change Alerts"
        description="USCIS policy and news updates detected by the scraper"
      />

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
        </div>
      ) : data?.length === 0 ? (
        <div className="text-center py-16">
          <Bell className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500 text-sm">No alerts yet — updates appear when scrapers detect changes</p>
        </div>
      ) : (
        <div className="space-y-3 max-w-2xl">
          {data?.map((alert) => (
            <Card
              key={alert.id}
              className={cn(
                "border-slate-200",
                !alert.is_read && "border-brand-200 bg-brand-50/30"
              )}
            >
              <CardContent className="pt-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline" className="text-xs">
                        {alert.source_type}
                      </Badge>
                      {!alert.is_read && (
                        <Badge className="text-xs bg-brand-600">New</Badge>
                      )}
                    </div>
                    <h3 className="font-medium text-slate-900 text-sm">{alert.title}</h3>
                    {alert.summary && (
                      <p className="text-xs text-slate-500 mt-1 line-clamp-2">{alert.summary}</p>
                    )}
                    <p className="text-xs text-slate-400 mt-2">
                      {new Date(alert.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex flex-col gap-1 shrink-0">
                    {alert.url && (
                      <a
                        href={alert.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-brand-600 hover:text-brand-700"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                    {!alert.is_read && (
                      <button
                        type="button"
                        onClick={() => readMut.mutate(alert.id)}
                        className="text-xs text-slate-500 hover:text-brand-600"
                      >
                        Mark read
                      </button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
