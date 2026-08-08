"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { ErrorState } from "@/components/common/error-state";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getAnalysis } from "@/lib/api/analyses";
import { formatShortDate } from "@/lib/formatters";

const statusTone: Record<string, "neutral" | "success" | "warning" | "danger"> = {
  pending: "neutral",
  running: "warning",
  completed: "success",
  failed: "danger",
};

export function AnalysisProgressFlow(): React.JSX.Element {
  const params = useParams<{ analysisId: string }>();
  const analysisId = params.analysisId;
  const query = useQuery({
    queryKey: ["analysis", analysisId],
    queryFn: () => getAnalysis(analysisId),
    refetchInterval: (queryInfo) => {
      const status = queryInfo.state.data?.analysis.status;
      return status === "pending" || status === "running" ? 3000 : false;
    },
  });

  if (query.isPending) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Loading analysis progress</CardTitle>
          <CardDescription>Fetching the current execution state for this analysis.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (query.error) {
    return <ErrorState message="Unable to load the analysis progress right now." />;
  }

  const analysis = query.data?.analysis;
  if (!analysis) {
    return <ErrorState message="The requested analysis could not be found." />;
  }

  return (
    <div className="grid gap-8">
      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader className="gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge tone={statusTone[analysis.status] ?? "neutral"}>{analysis.status}</StatusBadge>
              <StatusBadge tone="neutral">
                {analysis.current_stage ? analysis.current_stage.replace("_", " ") : "queued"}
              </StatusBadge>
            </div>
            <div className="space-y-2">
              <CardTitle className="text-3xl">Analysis started successfully.</CardTitle>
              <CardDescription className="max-w-2xl text-base leading-7">
                The backend returned a stable analysis ID and the progress page is polling for updates while the in-process execution runs.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="grid gap-4">
            <SummaryRow label="Analysis ID" value={analysis.id} />
            <SummaryRow label="Property ID" value={analysis.property_id} />
            <SummaryRow label="Version" value={String(analysis.version)} />
            <SummaryRow label="Created" value={formatShortDate(analysis.created_at)} />
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
              <CardTitle>Execution metadata</CardTitle>
              <CardDescription>
                While the analysis is running, this page shows lightweight status and stage updates.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>Status: <span className="font-medium text-foreground">{analysis.status}</span></p>
              <p>Stage: <span className="font-medium text-foreground">{analysis.current_stage || "pending"}</span></p>
              <p>Polling interval: <span className="font-medium text-foreground">3 seconds while active</span></p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Next workflow step</CardTitle>
              <CardDescription>
                Later phases will expand this page into the full progress and report experience.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="outline">
                <Link href="/">Start another property</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
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
