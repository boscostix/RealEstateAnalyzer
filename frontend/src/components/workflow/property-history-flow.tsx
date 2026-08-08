"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, History, RotateCcw } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErrorState } from "@/components/common/error-state";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getProperty, listPropertyAnalyses } from "@/lib/api/properties";
import { rerunAnalysis } from "@/lib/api/analyses";
import type { ApiClientError } from "@/lib/api/client";
import { formatCurrency, formatShortDate } from "@/lib/formatters";
import {
  buildRerunOverridePayload,
  EMPTY_RERUN_OVERRIDES,
  parentVersionLabel,
  type RerunOverrideFormValues,
} from "@/lib/history-workflow";

const overrideSchema = z.object({
  interest_rate_percent: z.string(),
  monthly_rent: z.string(),
  purchase_price: z.string(),
});

export function PropertyHistoryFlow(): React.JSX.Element {
  const params = useParams<{ propertyId: string }>();
  const router = useRouter();
  const propertyId = params.propertyId;
  const [expandedAnalysisId, setExpandedAnalysisId] = useState<string | null>(null);

  const propertyQuery = useQuery({
    queryKey: ["property", propertyId],
    queryFn: () => getProperty(propertyId),
  });
  const analysesQuery = useQuery({
    queryKey: ["property-analyses", propertyId],
    queryFn: () => listPropertyAnalyses(propertyId),
  });

  const form = useForm<RerunOverrideFormValues>({
    resolver: zodResolver(overrideSchema),
    defaultValues: EMPTY_RERUN_OVERRIDES,
  });

  const rerunMutation = useMutation({
    mutationFn: async ({
      analysisId,
      values,
    }: {
      analysisId: string;
      values: RerunOverrideFormValues;
    }) => {
      return rerunAnalysis(analysisId, buildRerunOverridePayload(values));
    },
    onSuccess: (response) => {
      router.push(`/analyses/${response.analysis.id}`);
    },
  });

  if (propertyQuery.isPending || analysesQuery.isPending) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Loading property history</CardTitle>
          <CardDescription>Fetching the property record and prior analysis versions.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (propertyQuery.error || analysesQuery.error) {
    return <ErrorState message="Unable to load the property history right now." />;
  }

  const property = propertyQuery.data?.property;
  const analyses = analysesQuery.data?.analyses ?? [];
  if (!property) {
    return <ErrorState message="The requested property could not be found." />;
  }

  const latestAnalysis = property.latest_analysis ?? analyses[0] ?? null;

  return (
    <div className="grid gap-8">
      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader className="gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge tone="success">Property history</StatusBadge>
              <StatusBadge tone="neutral">{`${property.analysis_count} analyses`}</StatusBadge>
            </div>
            <div className="space-y-2">
              <CardTitle className="text-3xl">
                {property.full_address ?? "Property detail"}
              </CardTitle>
              <CardDescription className="max-w-2xl text-base leading-7">
                Review prior analysis versions, open older reports, and rerun an analysis with assumption overrides while keeping historical records unchanged.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <MetricCard label="Provider" value={property.provider} />
            <MetricCard label="Current version" value={`v${property.current_version}`} />
            <MetricCard label="Analysis count" value={String(property.analysis_count)} />
            <MetricCard
              label="Verified asking price"
              value={formatCurrency(property.verified_property?.asking_price.final_value ?? null)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Latest analysis summary</CardTitle>
            <CardDescription>
              The most recent persisted analysis is highlighted here for quick navigation.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {latestAnalysis ? (
              <>
                <SummaryRow label="Version" value={`v${latestAnalysis.version}`} />
                <SummaryRow label="Status" value={latestAnalysis.status} />
                <SummaryRow
                  label="Created"
                  value={formatShortDate(latestAnalysis.created_at)}
                />
                <Button asChild>
                  <Link
                    href={
                      latestAnalysis.status === "completed"
                        ? `/analyses/${latestAnalysis.id}/report`
                        : `/analyses/${latestAnalysis.id}`
                    }
                  >
                    Open latest report
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </>
            ) : (
              <div className="rounded-2xl border border-border/70 bg-background/70 p-4 text-sm text-muted-foreground">
                No analyses have been created for this property yet.
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <History className="h-5 w-5 text-primary" />
            Analysis history
          </CardTitle>
          <CardDescription>
            Open any historical version, inspect parent lineage, or rerun with selective assumption overrides.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          {analyses.length > 0 ? (
            analyses.map((analysis) => {
              const rerunLabel = parentVersionLabel(analysis, analyses);
              const expanded = expandedAnalysisId === analysis.id;

              return (
                <div
                  className="rounded-3xl border border-border/70 bg-background/80 p-5"
                  key={analysis.id}
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-3">
                      <div className="flex flex-wrap items-center gap-3">
                        <StatusBadge tone="neutral">{`v${analysis.version}`}</StatusBadge>
                        <StatusBadge
                          tone={
                            analysis.status === "completed"
                              ? "success"
                              : analysis.status === "failed"
                                ? "danger"
                                : "warning"
                          }
                        >
                          {analysis.status}
                        </StatusBadge>
                        {rerunLabel ? <StatusBadge tone="warning">{rerunLabel}</StatusBadge> : null}
                      </div>
                      <div className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-3">
                        <div>Created {formatShortDate(analysis.created_at)}</div>
                        <div>
                          Stage {analysis.current_stage ? analysis.current_stage.replaceAll("_", " ") : "pending"}
                        </div>
                        <div>{analysis.parent_analysis_id ? "Derived from prior run" : "Original run"}</div>
                      </div>
                    </div>
                    <div className="flex flex-col gap-3 sm:flex-row">
                      <Button asChild variant="outline">
                        <Link href={`/analyses/${analysis.id}`}>
                          Open progress
                        </Link>
                      </Button>
                      <Button asChild>
                        <Link
                          href={
                            analysis.status === "completed"
                              ? `/analyses/${analysis.id}/report`
                              : `/analyses/${analysis.id}`
                          }
                        >
                          Open report
                          <ArrowRight className="ml-2 h-4 w-4" />
                        </Link>
                      </Button>
                      <Button
                        onClick={() => {
                          form.reset(EMPTY_RERUN_OVERRIDES);
                          setExpandedAnalysisId(expanded ? null : analysis.id);
                        }}
                        type="button"
                        variant="outline"
                      >
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Rerun
                      </Button>
                    </div>
                  </div>

                  {expanded ? (
                    <form
                      className="mt-5 grid gap-4 rounded-2xl border border-border/60 bg-background/70 p-4 md:grid-cols-3"
                      onSubmit={form.handleSubmit((values) =>
                        rerunMutation.mutate({
                          analysisId: analysis.id,
                          values,
                        }),
                      )}
                    >
                      <OverrideField
                        form={form}
                        helper="Optional override for the financing assumption."
                        label="Interest rate percent"
                        name="interest_rate_percent"
                        placeholder="7.10"
                      />
                      <OverrideField
                        form={form}
                        helper="Optional override for the income assumption."
                        label="Monthly rent"
                        name="monthly_rent"
                        placeholder="3500"
                      />
                      <OverrideField
                        form={form}
                        helper="Optional override for the purchase basis."
                        label="Purchase price"
                        name="purchase_price"
                        placeholder="430000"
                      />
                      {rerunMutation.error ? (
                        <div className="md:col-span-3 rounded-2xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger">
                          {mutationMessage(rerunMutation.error)}
                        </div>
                      ) : null}
                      <div className="md:col-span-3 flex flex-col gap-3 sm:flex-row">
                        <Button type="submit">
                          {rerunMutation.isPending ? "Starting rerun..." : "Create rerun"}
                        </Button>
                        <Button
                          onClick={() => {
                            form.reset(EMPTY_RERUN_OVERRIDES);
                            setExpandedAnalysisId(null);
                          }}
                          type="button"
                          variant="outline"
                        >
                          Cancel
                        </Button>
                      </div>
                    </form>
                  ) : null}
                </div>
              );
            })
          ) : (
            <div className="rounded-2xl border border-border/70 bg-background/70 p-4 text-sm text-muted-foreground">
              No analysis history is available for this property yet.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function OverrideField({
  label,
  helper,
  name,
  placeholder,
  form,
}: {
  label: string;
  helper: string;
  name: keyof RerunOverrideFormValues;
  placeholder: string;
  form: ReturnType<typeof useForm<RerunOverrideFormValues>>;
}): React.JSX.Element {
  const error = form.formState.errors[name];
  return (
    <div className="rounded-2xl border border-border/70 bg-background/80 p-4">
      <label className="text-sm font-semibold text-foreground" htmlFor={name}>
        {label}
      </label>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{helper}</p>
      <Input className="mt-3" id={name} placeholder={placeholder} {...form.register(name)} />
      {error ? <p className="mt-2 text-xs text-danger">{error.message}</p> : null}
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
    <div className="rounded-2xl border border-border/60 bg-background/70 p-3">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </div>
      <div className="mt-2 text-sm font-medium text-foreground">{value}</div>
    </div>
  );
}

function mutationMessage(error: unknown): string {
  if (error instanceof Error && "details" in error) {
    const apiError = error as ApiClientError;
    return apiError.details.message;
  }

  return error instanceof Error ? error.message : "Unable to start the rerun.";
}
