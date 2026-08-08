"use client";

import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Building2, DatabaseZap, Search, ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErrorState } from "@/components/common/error-state";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createProperty } from "@/lib/api/properties";
import type { ApiClientError } from "@/lib/api/client";
import { extractListing } from "@/lib/api/listings";
import type { PropertyExtractionPayload } from "@/lib/api/types";
import { getApiBaseUrl } from "@/lib/env";
import { formatCurrency } from "@/lib/formatters";
import { saveExtractionForProperty } from "@/lib/property-workflow";

const workflowSteps = [
  "Extract listing data",
  "Verify important property fields",
  "Set underwriting assumptions",
  "Run persisted analysis",
  "Review the investment memo",
];

const listingSchema = z.object({
  url: z.url("Paste a valid Zillow or Redfin listing URL."),
});

type ListingFormValues = z.infer<typeof listingSchema>;

export function ListingSubmissionFlow(): React.JSX.Element {
  const router = useRouter();
  const form = useForm<ListingFormValues>({
    resolver: zodResolver(listingSchema),
    defaultValues: {
      url: "https://www.zillow.com/homedetails/example",
    },
  });
  const extractionMutation = useMutation({
    mutationFn: async ({ url }: ListingFormValues): Promise<PropertyExtractionPayload> => {
      const response = await extractListing({ url });
      if (
        !response.success ||
        !response.provider ||
        !response.source_url ||
        !response.property ||
        !response.metadata ||
        !response.field_provenance
      ) {
        throw new Error("The backend did not return a usable extraction payload.");
      }

      return {
        provider: response.provider,
        source_url: response.source_url,
        property: response.property,
        metadata: response.metadata,
        field_provenance: response.field_provenance,
      };
    },
  });
  const createMutation = useMutation({
    mutationFn: async (extraction: PropertyExtractionPayload) => {
      const response = await createProperty({ property: extraction.property });
      saveExtractionForProperty(response.property.id, extraction);
      return response.property;
    },
    onSuccess: (property) => {
      router.push(`/properties/${property.id}/verify`);
    },
  });

  const extraction = extractionMutation.data;
  const missingCount = extraction?.metadata.fields_missing.length ?? 0;
  const submissionError = mutationMessage(extractionMutation.error) ?? mutationMessage(createMutation.error);

  return (
    <div className="grid gap-8">
      <section className="grid gap-8 lg:grid-cols-[1.45fr_0.95fr]">
        <Card className="overflow-hidden border-border/70 bg-[radial-gradient(circle_at_top_left,rgba(191,219,254,0.35),transparent_42%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))]">
          <CardHeader className="gap-5">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge tone="success">Phase 2 Submission</StatusBadge>
              <span className="text-sm text-muted-foreground">
                Backend: {getApiBaseUrl()}
              </span>
            </div>
            <div className="max-w-3xl space-y-4">
              <CardTitle className="text-4xl leading-tight md:text-5xl">
                Paste a listing, persist the property, and hand off to verification.
              </CardTitle>
              <CardDescription className="max-w-2xl text-base leading-7 text-muted-foreground">
                This demo flow extracts listing data from the backend, saves a stable property
                record, and opens a verification workspace where analysts can correct missing
                or inaccurate fields before underwriting begins.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
            <form
              className="space-y-4"
              onSubmit={form.handleSubmit((values) => extractionMutation.mutate(values))}
            >
              <label className="block text-sm font-medium text-foreground" htmlFor="listing-url">
                Property listing URL
              </label>
              <div className="flex flex-col gap-3 md:flex-row">
                <Input
                  {...form.register("url")}
                  id="listing-url"
                  placeholder="Paste a Zillow or Redfin URL"
                />
                <Button className="md:min-w-48" size="lg" type="submit">
                  {extractionMutation.isPending ? "Extracting..." : "Extract listing"}
                  <Search className="ml-2 h-4 w-4" />
                </Button>
              </div>
              {form.formState.errors.url ? (
                <p className="text-sm text-danger">{form.formState.errors.url.message}</p>
              ) : null}
              <p className="text-sm text-muted-foreground">
                The extracted property is persisted only after you review the preview and choose
                to continue.
              </p>
            </form>

            <div className="rounded-2xl border border-border/70 bg-background/70 p-5">
              <div className="mb-4 text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Workflow
              </div>
              <ol className="space-y-3">
                {workflowSteps.map((step, index) => (
                  <li className="flex items-center gap-3 text-sm text-foreground" key={step}>
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                      {index + 1}
                    </div>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-xl">
                <Building2 className="h-5 w-5 text-primary" />
                Extraction
              </CardTitle>
              <CardDescription>
                Listing extraction uses the existing backend provider pipeline and preserves
                field-level provenance for verification.
              </CardDescription>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-xl">
                <DatabaseZap className="h-5 w-5 text-primary" />
                Persistence
              </CardTitle>
              <CardDescription>
                Persisting creates a stable property ID that the rest of the workflow can rely on.
              </CardDescription>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-xl">
                <ShieldCheck className="h-5 w-5 text-primary" />
                Analyst Review
              </CardTitle>
              <CardDescription>
                Missing values stay editable so the analyst can complete the record before
                assumptions are entered.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {submissionError ? (
        <ErrorState message={submissionError} title="Submission flow needs attention" />
      ) : null}

      {extraction ? (
        <Card>
          <CardHeader className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-3">
                <CardTitle>Extraction preview</CardTitle>
                <StatusBadge tone={missingCount > 0 ? "warning" : "success"}>
                  {missingCount > 0 ? `${missingCount} fields missing` : "Ready to persist"}
                </StatusBadge>
              </div>
              <CardDescription>
                Review the extracted summary, then save the property and move into verification.
              </CardDescription>
            </div>
            <Button
              onClick={() => createMutation.mutate(extraction)}
              size="lg"
              type="button"
            >
              {createMutation.isPending ? "Saving property..." : "Save and verify"}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
            <div className="grid gap-4 md:grid-cols-2">
              <SummaryRow label="Address" value={extraction.property.address?.full_address} />
              <SummaryRow
                label="Asking price"
                value={formatCurrency(extraction.property.asking_price ?? null)}
              />
              <SummaryRow label="Bedrooms" value={stringValue(extraction.property.bedrooms)} />
              <SummaryRow label="Bathrooms" value={stringValue(extraction.property.bathrooms)} />
              <SummaryRow label="Square feet" value={stringValue(extraction.property.square_feet)} />
              <SummaryRow
                label="Property type"
                value={stringValue(extraction.property.property_type)}
              />
            </div>
            <div className="rounded-2xl border border-border/70 bg-muted/30 p-5">
              <div className="text-sm font-semibold text-foreground">Extraction details</div>
              <dl className="mt-4 grid gap-3 text-sm">
                <MetaRow label="Provider" value={extraction.provider} />
                <MetaRow label="Method" value={extraction.metadata.extraction_method} />
                <MetaRow label="Fields found" value={String(extraction.metadata.fields_found)} />
                <MetaRow
                  label="Warnings"
                  value={String(extraction.metadata.warnings.length)}
                />
              </dl>
              {missingCount > 0 ? (
                <div className="mt-4 space-y-2">
                  <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    Missing fields
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {extraction.metadata.fields_missing.map((field) => (
                      <StatusBadge key={field} tone="warning">
                        {field.replaceAll("_", " ")}
                      </StatusBadge>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function mutationMessage(error: unknown): string | null {
  if (!error) {
    return null;
  }

  if (error instanceof Error && "details" in error) {
    const apiError = error as ApiClientError;
    return apiError.details.message;
  }

  return error instanceof Error ? error.message : "Unexpected frontend error.";
}

function SummaryRow({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}): React.JSX.Element {
  return (
    <div className="rounded-2xl border border-border/60 bg-background/80 p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </div>
      <div className="mt-2 text-base font-semibold text-foreground">{value || "Missing"}</div>
    </div>
  );
}

function MetaRow({
  label,
  value,
}: {
  label: string;
  value: string;
}): React.JSX.Element {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium text-foreground">{value}</dd>
    </div>
  );
}

function stringValue(value: unknown): string {
  return value === null || value === undefined || value === "" ? "Missing" : String(value);
}
