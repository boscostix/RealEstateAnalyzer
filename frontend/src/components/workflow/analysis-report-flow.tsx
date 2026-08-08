"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { useEffect } from "react";

import { ErrorState } from "@/components/common/error-state";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getAnalysis } from "@/lib/api/analyses";
import { completedReportPath, humanizeStage, shouldPollAnalysis } from "@/lib/progress-workflow";
import { formatCurrency, formatPercent, formatShortDate } from "@/lib/formatters";

export function AnalysisReportFlow(): React.JSX.Element {
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

  useEffect(() => {
    const analysis = query.data?.analysis;
    if (!analysis) {
      return;
    }

    if (shouldPollAnalysis(analysis.status) || analysis.status === "failed") {
      router.replace(`/analyses/${analysis.id}`);
    }
  }, [query.data?.analysis, router]);

  if (query.isPending) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Loading completed analysis</CardTitle>
          <CardDescription>Preparing the completed report view for this analysis.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (query.error) {
    return <ErrorState message="Unable to load the completed analysis report." />;
  }

  const analysis = query.data?.analysis;
  if (!analysis) {
    return <ErrorState message="The requested analysis could not be found." />;
  }

  if (analysis.status !== "completed") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Waiting for report readiness</CardTitle>
          <CardDescription>
            This route is reserved for completed analyses. Returning to the progress page now.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const metrics = recordValue(analysis.underwriting, "metrics");
  const acquisition = recordValue(analysis.underwriting, "acquisition");

  return (
    <div className="grid gap-8">
      <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader className="gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge tone="success">completed</StatusBadge>
              <StatusBadge tone="neutral">
                {analysis.current_stage ? humanizeStage(analysis.current_stage) : "persistence"}
              </StatusBadge>
            </div>
            <div className="space-y-2">
              <CardTitle className="text-3xl">Completed analysis report</CardTitle>
              <CardDescription className="max-w-2xl text-base leading-7">
                This view renders the persisted completed analysis output and does not poll once the analysis is terminal.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <MetricCard label="NOI" value={formatCurrency(scalarValue(metrics, "noi"))} />
            <MetricCard
              label="Monthly cash flow"
              value={formatCurrency(scalarValue(metrics, "monthly_pre_tax_cash_flow"))}
            />
            <MetricCard
              label="Cap rate"
              value={formatPercent(percentFromDecimal(scalarValue(metrics, "cap_rate")))}
            />
            <MetricCard
              label="Cash-on-cash"
              value={formatPercent(percentFromDecimal(scalarValue(metrics, "cash_on_cash_return")))}
            />
            <MetricCard label="DSCR" value={stringValue(scalarValue(metrics, "dscr"))} />
            <MetricCard
              label="Cash required"
              value={formatCurrency(scalarValue(acquisition, "total_cash_required_at_closing"))}
            />
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Analysis summary</CardTitle>
              <CardDescription>Persisted identifiers and timestamps for this completed run.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 text-sm">
              <SummaryRow label="Analysis ID" value={analysis.id} />
              <SummaryRow label="Property ID" value={analysis.property_id} />
              <SummaryRow label="Version" value={String(analysis.version)} />
              <SummaryRow label="Created" value={formatShortDate(analysis.created_at)} />
              <SummaryRow label="Completed" value={formatShortDate(analysis.completed_at ?? null)} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Workflow links</CardTitle>
              <CardDescription>
                You can revisit progress, start over, or stay on this report view.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Button asChild variant="outline">
                <Link href={`/analyses/${analysis.id}`}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to progress
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href={completedReportPath(analysis.id)}>Refresh report route</Link>
              </Button>
              <Button asChild>
                <Link href="/">Start another property</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string;
}): React.JSX.Element {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/80 p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold text-foreground">{value}</div>
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

function recordValue(
  record: Record<string, unknown> | null | undefined,
  key: string,
): Record<string, unknown> | null {
  const value = record?.[key];
  return value && typeof value === "object" ? (value as Record<string, unknown>) : null;
}

function scalarValue(
  record: Record<string, unknown> | null | undefined,
  key: string,
): string | number | null {
  const value = record?.[key];
  return typeof value === "string" || typeof value === "number" ? value : null;
}

function percentFromDecimal(value: unknown): string | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const numeric = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(numeric)) {
    return null;
  }

  return String(numeric * 100);
}

function stringValue(value: unknown): string {
  return value === null || value === undefined || value === "" ? "N/A" : String(value);
}
