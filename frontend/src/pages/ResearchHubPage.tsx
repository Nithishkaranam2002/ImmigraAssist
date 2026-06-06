import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { BookOpen, ArrowRight, Loader2 } from "lucide-react"
import { platformService } from "@/services/platformService"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent } from "@/components/ui/card"

export function ResearchHubPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["research-hubs"],
    queryFn: platformService.listResearchHubs,
  })

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <PageHeader
        title="Visa Research Hubs"
        description="Curated starting points for common immigration pathways"
      />

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data?.map((hub) => (
            <Link key={hub.id} to={`/research/${hub.id}`}>
              <Card className="border-slate-200 hover:border-brand-300 hover:shadow-md transition-all h-full group">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center">
                      <BookOpen className="w-5 h-5 text-brand-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-slate-900 group-hover:text-brand-700">
                        {hub.title}
                      </h3>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-brand-500" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
