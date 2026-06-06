import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { CheckCircle, XCircle, Loader2, AlertTriangle } from "lucide-react"
import { platformService } from "@/services/platformService"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { toast } from "@/hooks/useToast"

export function ReviewQueuePage() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ["reviews"],
    queryFn: platformService.listReviews,
    refetchInterval: 30000,
  })

  const updateMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      platformService.updateReview(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reviews"] })
      toast("Review updated", "success")
    },
  })

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <PageHeader
        title="Human Review Queue"
        description="Low-confidence answers flagged for attorney review before client use"
      />

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
        </div>
      ) : data?.length === 0 ? (
        <div className="text-center py-16">
          <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto mb-3" />
          <p className="text-slate-600">No pending reviews — all clear</p>
        </div>
      ) : (
        <div className="space-y-4 max-w-3xl">
          {data?.map((item) => (
            <Card key={item.id} className="border-slate-200">
              <CardContent className="pt-5">
                <div className="flex items-start gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                  <p className="font-medium text-slate-900 text-sm">{item.query}</p>
                </div>
                <p className="text-xs text-slate-500 line-clamp-3 ml-6">{item.answer_preview}</p>
                <div className="flex gap-2 mt-4 ml-6">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={updateMut.isPending}
                    onClick={() => updateMut.mutate({ id: item.id, status: "approved" })}
                  >
                    <CheckCircle className="w-3.5 h-3.5 mr-1 text-emerald-600" /> Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={updateMut.isPending}
                    onClick={() => updateMut.mutate({ id: item.id, status: "rejected" })}
                  >
                    <XCircle className="w-3.5 h-3.5 mr-1 text-red-500" /> Reject
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
