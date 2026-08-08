"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, LoaderCircle, RotateCcw } from "lucide-react";
import { useEffect } from "react";

import { ErrorState } from "@/components/common/error-state";
import { PageLoadingState } from "@/components/common/page-loading-state";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getAnalysis, rerunAnalysis } from "@/lib/api/analyses";
import { formatShortDate } from "@/lib/formatters";
import {
  analysisHeadline,
  analysisSubhead,
  completedReportPath,
  deriveStageDescriptors,
  humanizeStage,
  shouldPollAnalysis,
} from "@/lib/progress-workflow";
import { cn } from "@/lib/utils";

const statusTone: Record<string, "neutral" | "success" | "warning" | "danger"> = {
  pending: "neutral",
  running: "warning",
  completed: "success",
  failed: "danger",
};

export function AnalysisProgressFlow(): React.JSX.Element {
  const params = useParams<{ analysisId: string }>();
  const router = useRouter();
  const analysisId = params.analysisId;
  const query = useQuery({
    queryKey: ["analysis", analysisId],
    queryFn: () => getAnalysis(analysisId),
    refetchInterval: (queryInfo) => {
      const status = queryInfo.state.data?.analysis.status;
      return shouldPollAnalysis(status) ? 3000 : false;
    },
  });
  const rerunMutation = useMutation({
    mutationFn: () => rerunAnalysis(analysisId, { assumption_overrides: {} }),
    onSuccess: (response) => {
      router.push(`/analyses/${response.analysis.id}`);
    },
  });

  useEffect(() => {
    const analysis = query.data?.analysis;
    if (analysis?.status !== "completed") {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      router.replace(completedReportPath(analysis.id));
    }, 900);

    return () => window.clearTimeout(timeoutId);
  }, [query.data?.analysis, router]);

  if (query.isPending) {
    return <PageLoadingState description="Fetching the current execution state for this analysis." title="Loading analysis progress" />;
  }

  if (query.error) {
    return <ErrorState message="Unable to load the analysis progress right now." />;
  }

  const analysis = query.data?.analysis;
  if (!analysis) {
    return <ErrorState message="The requested analysis could not be found." />;
  }
  const stages = deriveStageDescriptors(
    analysis.status,
    analysis.current_stage,
    analysis.failure_stage,
  );

  return (
    <div className="grid gap-8">
      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader className="gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge tone={statusTone[analysis.status] ?? "neutral"}>{analysis.status}</StatusBadge>
              <StatusBadge tone="neutral">
                {analysis.current_stage ? humanizeStage(analysis.current_stage) : "queued"}
              </StatusBadge>
            </div>
            <div className="space-y-2">
              <CardTitle className="text-3xl">{analysisHeadline(analysis)}</CardTitle>
              <CardDescription className="max-w-2xl text-base leading-7">
                {analysisSubhead(analysis)}
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="grid gap-4">
            <SummaryRow label="Analysis ID" value={analysis.id} />
            <SummaryRow label="Property ID" value={analysis.property_id} />
            <SummaryRow label="Version" value={String(analysis.version)} />
            <SummaryRow label="Created" value={formatShortDate(analysis.created_at)} />
            {analysis.status === "completed" ? (
              <div className="rounded-2xl border border-success/30 bg-success/5 p-4 text-sm text-success">
                Analysis complete. Redirecting to the report view now.
              </div>
            ) : null}
            {analysis.error_message ? (
              <div className="rounded-2xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger">
                {analysis.error_message}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Pipeline stages</CardTitle>
              <CardDescription>
                This view reflects only persisted status and stage data. It does not invent percentages.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {stages.map((stage) => (
                <div
                  className={cn(
                    "rounded-2xl border p-4",
                    stage.state === "completed" && "border-success/30 bg-success/5",
                    stage.state === "current" && "border-warning/30 bg-warning/5",
                    stage.state === "failed" && "border-danger/30 bg-danger/5",
                    stage.state === "upcoming" && "border-border/70 bg-background/70",
                  )}
                  key={stage.key}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-foreground">{stage.label}</div>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">
                        {stage.description}
                      </p>
                    </div>
                    <StatusBadge tone={stageTone(stage.state)}>{stage.state}</StatusBadge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Execution details</CardTitle>
              <CardDescription>
                Polling stops automatically when the persisted status becomes `completed` or `failed`.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground">
              <p>
                Status: <span className="font-medium text-foreground">{analysis.status}</span>
              </p>
              <p>
                Current stage:{" "}
                <span className="font-medium text-foreground">
                  {analysis.current_stage ? humanizeStage(analysis.current_stage) : "pending"}
                </span>
              </p>
              <p>
                Polling:{" "}
                <span className="font-medium text-foreground">
                  {shouldPollAnalysis(analysis.status) ? "Every 3 seconds while active" : "Stopped"}
                </span>
              </p>
              {analysis.status === "failed" ? (
                <Button
                  onClick={() => rerunMutation.mutate()}
                  type="button"
                  variant="outline"
                >
                  {rerunMutation.isPending ? (
                    <>
                      <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                      Starting rerun...
                    </>
                  ) : (
                    <>
                      <RotateCcw className="mr-2 h-4 w-4" />
                      Rerun analysis
                    </>
                  )}
                </Button>
              ) : null}
              {analysis.status === "completed" ? (
                <Button asChild>
                  <Link href={completedReportPath(analysis.id)}>
                    Open report
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              ) : null}
              <Button asChild variant="outline">
                <Link href={`/properties/${analysis.property_id}`}>
                  Property history
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/">Start another property</Link>
              </Button>
              {rerunMutation.error ? (
                <div
                  aria-live="polite"
                  className="rounded-2xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger"
                  role="alert"
                >
                  Unable to start the rerun right now. Try again from the property history page if this keeps happening.
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}

function stageTone(state: "completed" | "current" | "upcoming" | "failed") {
  switch (state) {
    case "completed":
      return "success";
    case "current":
      return "warning";
    case "failed":
      return "danger";
    default:
      return "neutral";
  }
}

function SummaryRow({
  label,
  value,
}: {
  label: string;
  value: string;
}): React.JSX.Element {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-border/60 bg-background/70 p-3">
      <div className="text-muted-foreground">{label}</div>
      <div className="text-right font-medium text-foreground">{value}</div>
    </div>
  );
}
