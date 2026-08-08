"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { useEffect } from "react";

import { ErrorState } from "@/components/common/error-state";
import { EmptyState } from "@/components/common/empty-state";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getAnalysis } from "@/lib/api/analyses";
import { listPropertyAnalyses } from "@/lib/api/properties";
import type { CommitteeReason } from "@/lib/api/types";
import { parentVersionLabel, versionNavigation } from "@/lib/history-workflow";
import {
  completedReportPath,
  humanizeStage,
  shouldPollAnalysis,
} from "@/lib/progress-workflow";
import {
  deriveOfferSection,
  executiveSummaryLines,
  recommendationLabel,
  recommendationTone,
  riskTone,
  salesComparableRows,
  rentalComparableRows,
  scenarioCards,
  stressTestCards,
  evidencePanelData,
} from "@/lib/report-workflow";
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
  const historyQuery = useQuery({
    enabled: Boolean(query.data?.analysis.property_id),
    queryKey: ["property-analyses", query.data?.analysis.property_id],
    queryFn: () => listPropertyAnalyses(query.data!.analysis.property_id),
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

  const committee = analysis.investment_committee;
  const analyses = historyQuery.data?.analyses ?? [];
  const metrics = recordValue(analysis.underwriting, "metrics");
  const acquisition = recordValue(analysis.underwriting, "acquisition");
  const maximumOffer = recordValue(analysis.underwriting, "maximum_offer");
  const offerSection = deriveOfferSection(analysis);
  const summaryLines = executiveSummaryLines(committee);
  const scenarioItems = scenarioCards(analysis);
  const stressItems = stressTestCards(analysis);
  const salesRows = salesComparableRows(analysis);
  const rentalRows = rentalComparableRows(analysis);
  const evidence = evidencePanelData(analysis);
  const materialRisks = committee?.material_risks ?? [];
  const missingInformation = [
    ...(committee?.missing_information ?? []).map((item) => ({
      title: item.item,
      detail: item.decision_impact,
      meta: `${item.materiality} materiality`,
    })),
    ...(analysis.agent_research?.missing_information ?? []).map((item) => ({
      title: item,
      detail: "Identified by the agent research synthesis as still missing.",
      meta: "agent research",
    })),
  ];
  const whatMustBeTrue = committee?.what_must_be_true ?? [];
  const diligenceItems = [
    ...(committee?.due_diligence_checklist ?? []).map((item) => ({
      title: item.action,
      detail: item.reason,
      meta: `${item.priority} priority · ${item.timing.replaceAll("_", " ")}`,
    })),
    ...(analysis.agent_research?.due_diligence_questions ?? []).map((item) => ({
      title: item,
      detail: "Agent research follow-up question.",
      meta: "agent research",
    })),
  ];
  const riskFindings = (analysis.agent_research?.consolidated_findings ?? []).filter((finding) =>
    finding.category.toLowerCase().includes("risk"),
  );
  const lineageLabel = parentVersionLabel(analysis, analyses);
  const navigation = versionNavigation(analysis.id, analyses);

  return (
    <div className="grid gap-8">
      <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <Card className="overflow-hidden border-border/70 bg-[radial-gradient(circle_at_top_left,rgba(190,242,100,0.14),transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))] lg:col-span-2">
          <CardHeader className="gap-5">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge tone="success">completed</StatusBadge>
              <StatusBadge tone="neutral">
                {analysis.current_stage ? humanizeStage(analysis.current_stage) : "persistence"}
              </StatusBadge>
              {committee ? (
                <StatusBadge tone={recommendationTone(committee.recommendation)}>
                  {recommendationLabel(committee.recommendation)}
                </StatusBadge>
              ) : (
                <StatusBadge tone="neutral">Recommendation unavailable</StatusBadge>
              )}
              <StatusBadge tone="neutral">{`v${analysis.version}`}</StatusBadge>
              {lineageLabel ? <StatusBadge tone="warning">{lineageLabel}</StatusBadge> : null}
            </div>
            <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
              <div className="space-y-4">
                <CardTitle className="text-4xl leading-tight">
                  {committee
                    ? recommendationLabel(committee.recommendation)
                    : "Completed analysis report"}
                </CardTitle>
                <CardDescription className="max-w-3xl text-base leading-7 text-muted-foreground">
                  {committee?.recommendation_summary ??
                    "This completed analysis does not include an investment committee recommendation summary yet."}
                </CardDescription>
                {committee ? (
                  <div className="flex flex-wrap gap-3 text-sm">
                    <HeroChip
                      label="Recommendation confidence"
                      value={formatPercent(percentFromDecimal(committee.recommendation_confidence))}
                    />
                    <HeroChip
                      label="Asking price"
                      value={formatCurrency(committee.asking_price ?? null)}
                    />
                    <HeroChip
                      label="Supported high"
                      value={formatCurrency(offerSection.supportedHigh)}
                    />
                  </div>
                ) : null}
              </div>
              <div className="rounded-3xl border border-border/70 bg-background/80 p-5">
                <div className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Executive Summary
                </div>
                {summaryLines.length > 0 ? (
                  <ul className="mt-4 grid gap-3 text-sm leading-6 text-foreground">
                    {summaryLines.map((line) => (
                      <li
                        className="rounded-2xl border border-border/60 bg-background/70 p-3"
                        key={line}
                      >
                        {line}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="mt-4 rounded-2xl border border-border/60 bg-background/70 p-4 text-sm text-muted-foreground">
                    Executive summary details are not available for this completed analysis.
                  </div>
                )}
              </div>
            </div>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Investment Thesis</CardTitle>
            <CardDescription>
              This thesis is rendered directly from the completed investment committee output.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {committee?.investment_thesis ? (
              <p className="text-sm leading-7 text-foreground">{committee.investment_thesis}</p>
            ) : (
              <EmptyState
                message="The completed analysis did not persist an investment thesis."
                title="No thesis available"
              />
            )}
            <div className="grid gap-3">
              <HighlightRow
                label="Strongest upside"
                value={committee?.strongest_upside ?? "Not available"}
              />
              <HighlightRow
                label="Strongest downside"
                value={committee?.strongest_downside ?? "Not available"}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Core Metrics</CardTitle>
            <CardDescription>
              Metric cards are displayed from persisted underwriting outputs only.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
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

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Offer Range</CardTitle>
            <CardDescription>
              Thresholds are displayed from persisted committee and underwriting values. The frontend does not recalculate them.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
            {offerSection.hasMeaningfulData ? (
              <>
                <div className="grid gap-4 sm:grid-cols-2">
                  <MetricCard label="Asking price" value={formatCurrency(offerSection.askingPrice)} />
                  <MetricCard
                    label="Supported offer low"
                    value={formatCurrency(offerSection.supportedLow)}
                  />
                  <MetricCard
                    label="Supported offer high"
                    value={formatCurrency(offerSection.supportedHigh)}
                  />
                  <MetricCard
                    label="Binding maximum"
                    value={formatCurrency(offerSection.bindingMaximum)}
                  />
                  <MetricCard
                    label="Asking gap"
                    value={formatCurrency(offerSection.askingGap)}
                  />
                  <MetricCard
                    label="Break-even threshold"
                    value={formatCurrency(scalarValue(maximumOffer, "break_even_cash_flow_price"))}
                  />
                </div>
                <div className="rounded-3xl border border-border/70 bg-background/80 p-5">
                  <div className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    Offer Basis
                  </div>
                  <div className="mt-4 grid gap-3">
                    {offerSection.basis.length > 0 ? (
                      offerSection.basis.map((basis) => (
                        <div
                          className="rounded-2xl border border-border/60 bg-background/70 p-4"
                          key={`${basis.label}-${basis.description}`}
                        >
                          <div className="flex items-center justify-between gap-4">
                            <div className="text-sm font-semibold text-foreground">{basis.label}</div>
                            <div className="text-sm font-semibold text-foreground">
                              {formatCurrency(basis.value)}
                            </div>
                          </div>
                          <p className="mt-2 text-sm leading-6 text-muted-foreground">
                            {basis.description}
                          </p>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-2xl border border-border/60 bg-background/70 p-4 text-sm text-muted-foreground">
                        No persisted offer-basis entries were available on this completed analysis.
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <EmptyState
                message="This completed analysis did not persist enough offer data to render supported thresholds."
                title="No offer thresholds available"
              />
            )}
          </CardContent>
        </Card>

        <ReasonSection
          description="These points come directly from the persisted investment committee output."
          reasons={committee?.reasons_to_proceed ?? []}
          title="Reasons To Proceed"
        />
        <ReasonSection
          description="These concerns come directly from the persisted investment committee output."
          reasons={committee?.reasons_not_to_proceed ?? []}
          title="Reasons Not To Proceed"
        />

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Deep Analysis</CardTitle>
            <CardDescription>
              Expand the sections below to inspect comparables, scenarios, stress tests, risks, missing information, diligence, and evidence.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <ExpandableSection
              defaultOpen
              description="Persisted rental comparable results and summary statistics from the research package."
              title="Rental Comparables"
            >
              {analysis.research?.rental_comps ? (
                <div className="grid gap-4">
                  <ComparableSummaryGrid
                    items={[
                      {
                        label: "Comparables",
                        value: stringValue(
                          analysis.research.rental_comps.data.summary.comparable_count,
                        ),
                      },
                      {
                        label: "Median rent",
                        value: formatCurrency(
                          analysis.research.rental_comps.data.summary.median_monthly_rent ?? null,
                        ),
                      },
                      {
                        label: "Estimated rent range",
                        value: formatRange(
                          analysis.research.rental_comps.data.summary.estimated_rent_range?.low,
                          analysis.research.rental_comps.data.summary.estimated_rent_range?.high,
                        ),
                      },
                    ]}
                  />
                  <ComparableTable rows={rentalRows} />
                </div>
              ) : (
                <InlineEmpty message="No rental comparables were persisted on this completed analysis." />
              )}
            </ExpandableSection>

            <ExpandableSection
              description="Persisted sales comparable results and summary statistics from the research package."
              title="Sales Comparables"
            >
              {analysis.research?.sales_comps ? (
                <div className="grid gap-4">
                  <ComparableSummaryGrid
                    items={[
                      {
                        label: "Comparables",
                        value: stringValue(
                          analysis.research.sales_comps.data.summary.comparable_count,
                        ),
                      },
                      {
                        label: "Median sold price",
                        value: formatCurrency(
                          analysis.research.sales_comps.data.summary.median_sold_price ?? null,
                        ),
                      },
                      {
                        label: "Sold price range",
                        value: formatRange(
                          analysis.research.sales_comps.data.summary.sold_price_range?.low,
                          analysis.research.sales_comps.data.summary.sold_price_range?.high,
                        ),
                      },
                    ]}
                  />
                  <ComparableTable rows={salesRows} />
                </div>
              ) : (
                <InlineEmpty message="No sales comparables were persisted on this completed analysis." />
              )}
            </ExpandableSection>

            <ExpandableSection
              description="Scenario outputs from the persisted underwriting analysis."
              title="Scenario Analysis"
            >
              {scenarioItems.length > 0 ? (
                <div className="grid gap-3 md:grid-cols-2">
                  {scenarioItems.map((scenario) => (
                    <div
                      className="rounded-2xl border border-border/70 bg-background/80 p-4"
                      key={scenario.name}
                    >
                      <div className="text-sm font-semibold text-foreground">{scenario.name}</div>
                      <div className="mt-3 grid gap-2 text-sm">
                        <ScenarioMetric
                          label="Monthly cash flow"
                          value={formatCurrency(scenario.monthlyCashFlow)}
                        />
                        <ScenarioMetric
                          label="Cap rate"
                          value={formatPercent(percentFromDecimal(scenario.capRate))}
                        />
                        <ScenarioMetric
                          label="Cash-on-cash"
                          value={formatPercent(percentFromDecimal(scenario.cashOnCash))}
                        />
                      </div>
                      {scenario.adjustments.length > 0 ? (
                        <div className="mt-4 flex flex-wrap gap-2">
                          {scenario.adjustments.map(([key, value]) => (
                            <StatusBadge key={`${scenario.name}-${key}`} tone="neutral">
                              {`${key}: ${value}`}
                            </StatusBadge>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <InlineEmpty message="No scenario outputs were persisted on this completed analysis." />
              )}
            </ExpandableSection>

            <ExpandableSection
              description="Stress-test results from the persisted underwriting analysis."
              title="Stress Tests"
            >
              {stressItems.length > 0 ? (
                <div className="grid gap-3">
                  {stressItems.map((stress) => (
                    <div
                      className="rounded-2xl border border-border/70 bg-background/80 p-4"
                      key={stress.identifier}
                    >
                      <div className="flex flex-wrap items-center gap-3">
                        <div className="text-sm font-semibold text-foreground">
                          {stress.identifier}
                        </div>
                        <StatusBadge tone={stress.remainsPositive ? "success" : "danger"}>
                          {stress.remainsPositive ? "cash flow remains positive" : "cash flow pressured"}
                        </StatusBadge>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        {stress.description}
                      </p>
                      <div className="mt-4 grid gap-2 sm:grid-cols-3">
                        <ScenarioMetric
                          label="Monthly cash flow delta"
                          value={formatCurrency(stress.monthlyCashFlowDelta)}
                        />
                        <ScenarioMetric
                          label="Annual cash flow delta"
                          value={formatCurrency(stress.annualCashFlowDelta)}
                        />
                        <ScenarioMetric
                          label="Additional cash required"
                          value={formatCurrency(stress.additionalCashRequired)}
                        />
                      </div>
                      {stress.changedAssumptions.length > 0 ? (
                        <div className="mt-4 flex flex-wrap gap-2">
                          {stress.changedAssumptions.map(([key, value]) => (
                            <StatusBadge key={`${stress.identifier}-${key}`} tone="neutral">
                              {`${key}: ${value}`}
                            </StatusBadge>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <InlineEmpty message="No stress-test outputs were persisted on this completed analysis." />
              )}
            </ExpandableSection>

            <ExpandableSection
              description="Material committee risks and persisted risk-related agent findings."
              title="Risk Analysis"
            >
              {materialRisks.length > 0 || riskFindings.length > 0 ? (
                <div className="grid gap-3">
                  {materialRisks.map((risk) => (
                    <div
                      className="rounded-2xl border border-border/70 bg-background/80 p-4"
                      key={`${risk.category}-${risk.title}`}
                    >
                      <div className="flex flex-wrap items-center gap-3">
                        <div className="text-sm font-semibold text-foreground">{risk.title}</div>
                        <StatusBadge tone={riskTone(risk.severity)}>{risk.severity}</StatusBadge>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        {risk.explanation}
                      </p>
                      {risk.financial_impact ? (
                        <p className="mt-2 text-sm text-foreground">
                          Financial impact: {risk.financial_impact}
                        </p>
                      ) : null}
                    </div>
                  ))}
                  {riskFindings.map((finding) => (
                    <div
                      className="rounded-2xl border border-border/70 bg-background/80 p-4"
                      key={finding.finding_id}
                    >
                      <div className="flex flex-wrap items-center gap-3">
                        <div className="text-sm font-semibold text-foreground">{finding.title}</div>
                        <StatusBadge tone={riskTone(finding.severity)}>{finding.severity}</StatusBadge>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        {finding.finding}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <InlineEmpty message="No persisted risk section was available for this completed analysis." />
              )}
            </ExpandableSection>

            <ExpandableSection
              description="Missing data that still matters to the investment decision."
              title="Missing Information"
            >
              {missingInformation.length > 0 ? (
                <SimpleItemList items={missingInformation} />
              ) : (
                <InlineEmpty message="No missing-information items were persisted on this completed analysis." />
              )}
            </ExpandableSection>

            <ExpandableSection
              description="Required deal truths and gating conditions from the investment committee output."
              title="What Must Be True"
            >
              {whatMustBeTrue.length > 0 ? (
                <div className="grid gap-3">
                  {whatMustBeTrue.map((item) => (
                    <div
                      className="rounded-2xl border border-border/70 bg-background/80 p-4"
                      key={item.condition}
                    >
                      <div className="text-sm font-semibold text-foreground">{item.condition}</div>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        Requirement: {item.threshold_or_requirement}
                      </p>
                      <p className="mt-2 text-sm text-foreground">
                        Current status: {item.current_status}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <InlineEmpty message="No what-must-be-true conditions were persisted on this completed analysis." />
              )}
            </ExpandableSection>

            <ExpandableSection
              description="Follow-up diligence work from the investment committee and agent research outputs."
              title="Due-Diligence Checklist"
            >
              {diligenceItems.length > 0 ? (
                <SimpleItemList items={diligenceItems} />
              ) : (
                <InlineEmpty message="No due-diligence checklist items were persisted on this completed analysis." />
              )}
            </ExpandableSection>

            <ExpandableSection
              description="Traceable citations and evidence references supporting the rendered report."
              title="Evidence and Sources"
            >
              {evidence.researchCitations.length > 0 || evidence.evidenceReferences.length > 0 ? (
                <div className="grid gap-6 lg:grid-cols-2">
                  <div className="grid gap-3">
                    <div className="text-sm font-semibold text-foreground">Research citations</div>
                    {evidence.researchCitations.length > 0 ? (
                      evidence.researchCitations.map((citation) => (
                        <a
                          className="rounded-2xl border border-border/70 bg-background/80 p-4 text-sm text-foreground hover:border-primary/40"
                          href={citation.url}
                          key={`${citation.label}-${citation.url}`}
                          rel="noreferrer"
                          target="_blank"
                        >
                          <div className="font-semibold">{citation.label}</div>
                          <div className="mt-2 break-all text-muted-foreground">{citation.url}</div>
                          <div className="mt-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                            {citation.note}
                          </div>
                        </a>
                      ))
                    ) : (
                      <InlineEmpty message="No research citations were persisted on this completed analysis." />
                    )}
                  </div>
                  <div className="grid gap-3">
                    <div className="text-sm font-semibold text-foreground">Evidence references</div>
                    {evidence.evidenceReferences.length > 0 ? (
                      evidence.evidenceReferences.map((reference) => (
                        <div
                          className="rounded-2xl border border-border/70 bg-background/80 p-4"
                          key={`${reference.sourceId}-${reference.locator}`}
                        >
                          <div className="text-sm font-semibold text-foreground">
                            {reference.sourceId}
                          </div>
                          <div className="mt-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                            {reference.sourceType}
                          </div>
                          <p className="mt-2 text-sm text-foreground">{reference.locator}</p>
                          <p className="mt-2 text-sm leading-6 text-muted-foreground">
                            {reference.excerpt}
                          </p>
                        </div>
                      ))
                    ) : (
                      <InlineEmpty message="No evidence references were persisted on this completed analysis." />
                    )}
                  </div>
                </div>
              ) : (
                <InlineEmpty message="No traceable citations or evidence references were persisted on this completed analysis." />
              )}
            </ExpandableSection>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Analysis Summary</CardTitle>
            <CardDescription>
              Persisted identifiers and timestamps for this completed run.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <SummaryRow label="Analysis ID" value={analysis.id} />
            <SummaryRow label="Property ID" value={analysis.property_id} />
            <SummaryRow label="Version" value={String(analysis.version)} />
            <SummaryRow label="Created" value={formatShortDate(analysis.created_at)} />
            <SummaryRow label="Completed" value={formatShortDate(analysis.completed_at ?? null)} />
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Workflow Links</CardTitle>
            <CardDescription>
              You can navigate between versions, revisit property history, or start another property.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <Button asChild variant="outline">
              <Link href={`/analyses/${analysis.id}`}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to progress
              </Link>
            </Button>
            {navigation.previous ? (
              <Button asChild variant="outline">
                <Link href={`/analyses/${navigation.previous.id}/report`}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Open v{navigation.previous.version}
                </Link>
              </Button>
            ) : null}
            {navigation.next ? (
              <Button asChild variant="outline">
                <Link href={`/analyses/${navigation.next.id}/report`}>
                  Open v{navigation.next.version}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            ) : null}
            <Button asChild variant="outline">
              <Link href={`/properties/${analysis.property_id}`}>Property history</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href={completedReportPath(analysis.id)}>Refresh report route</Link>
            </Button>
            <Button asChild>
              <Link href="/">Start another property</Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function ExpandableSection({
  title,
  description,
  children,
  defaultOpen = false,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}): React.JSX.Element {
  return (
    <details className="group rounded-3xl border border-border/70 bg-background/60" open={defaultOpen}>
      <summary className="cursor-pointer list-none px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-lg font-semibold text-foreground">{title}</div>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
          </div>
          <StatusBadge tone="neutral">expand</StatusBadge>
        </div>
      </summary>
      <div className="border-t border-border/70 px-5 py-5">{children}</div>
    </details>
  );
}

function ComparableSummaryGrid({
  items,
}: {
  items: Array<{ label: string; value: string }>;
}): React.JSX.Element {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {items.map((item) => (
        <MetricCard key={item.label} label={item.label} value={item.value} />
      ))}
    </div>
  );
}

function ComparableTable({
  rows,
}: {
  rows: Array<{
    address: string;
    primary: string;
    secondary: string;
    tertiary: string;
    link?: string | null;
  }>;
}): React.JSX.Element {
  if (rows.length === 0) {
    return <InlineEmpty message="No comparable rows were persisted for this section." />;
  }

  return (
    <div className="grid gap-3">
      {rows.map((row) => (
        <div
          className="rounded-2xl border border-border/70 bg-background/80 p-4"
          key={`${row.address}-${row.primary}`}
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm font-semibold text-foreground">{row.address}</div>
            {row.link ? (
              <a
                className="text-sm font-medium text-primary hover:underline"
                href={row.link}
                rel="noreferrer"
                target="_blank"
              >
                Source
              </a>
            ) : null}
          </div>
          <div className="mt-3 grid gap-2 text-sm text-muted-foreground sm:grid-cols-3">
            <div>{row.primary}</div>
            <div>{row.secondary}</div>
            <div>{row.tertiary}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function ScenarioMetric({
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

function SimpleItemList({
  items,
}: {
  items: Array<{ title: string; detail: string; meta: string }>;
}): React.JSX.Element {
  return (
    <div className="grid gap-3">
      {items.map((item) => (
        <div
          className="rounded-2xl border border-border/70 bg-background/80 p-4"
          key={`${item.title}-${item.meta}`}
        >
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-sm font-semibold text-foreground">{item.title}</div>
            <StatusBadge tone="neutral">{item.meta}</StatusBadge>
          </div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.detail}</p>
        </div>
      ))}
    </div>
  );
}

function InlineEmpty({ message }: { message: string }): React.JSX.Element {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/70 p-4 text-sm text-muted-foreground">
      {message}
    </div>
  );
}

function HeroChip({
  label,
  value,
}: {
  label: string;
  value: string;
}): React.JSX.Element {
  return (
    <div className="rounded-full border border-border/70 bg-background/80 px-4 py-2">
      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-sm font-semibold text-foreground">{value}</div>
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

function HighlightRow({
  label,
  value,
}: {
  label: string;
  value: string;
}): React.JSX.Element {
  return (
    <div className="rounded-2xl border border-border/60 bg-background/70 p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </div>
      <p className="mt-2 text-sm leading-6 text-foreground">{value}</p>
    </div>
  );
}

function ReasonSection({
  title,
  description,
  reasons,
}: {
  title: string;
  description: string;
  reasons: CommitteeReason[];
}): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {reasons.length > 0 ? (
          reasons.map((reason) => (
            <div
              className="rounded-2xl border border-border/70 bg-background/80 p-4"
              key={`${reason.title}-${reason.explanation}`}
            >
              <div className="flex flex-wrap items-center gap-3">
                <div className="text-sm font-semibold text-foreground">{reason.title}</div>
                <StatusBadge tone="neutral">{reason.importance}</StatusBadge>
              </div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{reason.explanation}</p>
            </div>
          ))
        ) : (
          <EmptyState
            message="The completed analysis did not persist any items for this section."
            title={`No ${title.toLowerCase()} available`}
          />
        )}
      </CardContent>
    </Card>
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

function formatRange(
  low: string | number | null | undefined,
  high: string | number | null | undefined,
): string {
  if (low == null && high == null) {
    return "N/A";
  }

  return `${formatCurrency(low ?? null)} - ${formatCurrency(high ?? null)}`;
}
