"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, RefreshCcw } from "lucide-react";
import { useEffect, useMemo } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { ErrorState } from "@/components/common/error-state";
import { PageLoadingState } from "@/components/common/page-loading-state";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getProperty, updateProperty, verifyProperty } from "@/lib/api/properties";
import type { ApiClientError } from "@/lib/api/client";
import {
  buildUpdatedProperty,
  buildVerificationRequest,
  createFormValues,
  deriveFieldStatus,
  loadExtractionForProperty,
  VERIFICATION_FIELD_CONFIG,
} from "@/lib/property-workflow";
import { formatCurrency } from "@/lib/formatters";

import { VerificationStatusBadge } from "./verification-status-badge";

const verificationSchema = z.object({
  full_address: z.string(),
  asking_price: z.string(),
  bedrooms: z.string(),
  bathrooms: z.string(),
  square_feet: z.string(),
  lot_square_feet: z.string(),
  year_built: z.string(),
  annual_property_tax: z.string(),
  annual_hoa: z.string(),
  property_type: z.string(),
});

type VerificationFormValues = z.infer<typeof verificationSchema>;

const EMPTY_VERIFICATION_VALUES: VerificationFormValues = {
  full_address: "",
  asking_price: "",
  bedrooms: "",
  bathrooms: "",
  square_feet: "",
  lot_square_feet: "",
  year_built: "",
  annual_property_tax: "",
  annual_hoa: "",
  property_type: "",
};

export function PropertyVerificationFlow(): React.JSX.Element {
  const params = useParams<{ propertyId: string }>();
  const router = useRouter();
  const propertyId = params.propertyId;
  const propertyQuery = useQuery({
    queryKey: ["property", propertyId],
    queryFn: () => getProperty(propertyId),
  });
  const form = useForm<VerificationFormValues>({
    resolver: zodResolver(verificationSchema),
    defaultValues: EMPTY_VERIFICATION_VALUES,
  });

  const extraction = useMemo(
    () => loadExtractionForProperty(propertyId),
    [propertyId],
  );

  useEffect(() => {
    if (propertyQuery.data?.property) {
      form.reset(
        createFormValues(
          propertyQuery.data.property.property,
          propertyQuery.data.property.verified_property,
        ),
      );
    }
  }, [form, propertyQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async (values: VerificationFormValues) => {
      if (!extraction) {
        throw new Error(
          "The browser no longer has the extraction context for this property. Start again from the landing page for this demo flow.",
        );
      }

      const propertyDetail = propertyQuery.data?.property;
      if (!propertyDetail?.property) {
        throw new Error("The persisted property snapshot is unavailable.");
      }

      const verificationPayload = buildVerificationRequest(extraction, values);
      const verificationResponse = await verifyProperty({
        extraction,
        corrections: verificationPayload.corrections,
        confirmed_fields: verificationPayload.confirmed_fields,
      });

      if (!verificationResponse.property) {
        throw new Error("The backend did not return a verified property snapshot.");
      }

      const updatedProperty = buildUpdatedProperty(propertyDetail.property, values);
      const currentVersion = propertyDetail.current_version + 1;

      return updateProperty(propertyId, {
        property: updatedProperty,
        verified_property: verificationResponse.property,
        current_version: currentVersion,
      });
    },
    onSuccess: () => {
      router.push(`/properties/${propertyId}/assumptions`);
    },
  });

  const watchedValues = useWatch({
    control: form.control,
  });
  const values: VerificationFormValues = {
    ...EMPTY_VERIFICATION_VALUES,
    ...watchedValues,
  };
  const propertyDetail = propertyQuery.data?.property;
  const submissionError = mutationMessage(saveMutation.error);

  if (propertyQuery.isPending) {
    return <PageLoadingState description="Fetching the persisted property and verification context." title="Loading property verification" />;
  }

  if (propertyQuery.error) {
    return (
      <ErrorState
        message={mutationMessage(propertyQuery.error) ?? "Unable to load the selected property."}
      />
    );
  }

  if (!propertyDetail?.property) {
    return (
      <ErrorState
        message="This property does not have a normalized property snapshot to verify."
        title="Property snapshot missing"
      />
    );
  }

  if (!extraction) {
    return (
      <ErrorState
        actionLabel="Return to landing page"
        message="This demo keeps extraction context in the browser session while you move into verification. If the page was refreshed or reopened later, start the workflow again from the landing page."
        onAction={() => router.push("/")}
        title="Extraction context unavailable"
      />
    );
  }

  const correctedCount = VERIFICATION_FIELD_CONFIG.filter(
    (field) =>
      deriveFieldStatus(field.key, values, extraction, propertyDetail.verified_property) ===
      "corrected",
  ).length;
  const missingCount = VERIFICATION_FIELD_CONFIG.filter(
    (field) =>
      deriveFieldStatus(field.key, values, extraction, propertyDetail.verified_property) ===
      "missing",
  ).length;

  return (
    <div className="grid gap-8">
      <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader className="gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge tone="success">Verification</StatusBadge>
              <StatusBadge tone={missingCount > 0 ? "warning" : "neutral"}>
                {missingCount > 0 ? `${missingCount} missing` : "All key fields filled"}
              </StatusBadge>
              {correctedCount > 0 ? (
                <StatusBadge tone="warning">{`${correctedCount} corrected`}</StatusBadge>
              ) : null}
            </div>
            <div className="space-y-2">
              <CardTitle className="text-3xl">
                Verify the property data before assumptions are entered.
              </CardTitle>
              <CardDescription className="max-w-2xl text-base leading-7">
                Confirm extracted values, fix anything inaccurate, and fill in blanks so the
                next step can build assumptions from a clean property snapshot.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <form
              className="grid gap-4 md:grid-cols-2"
              onSubmit={form.handleSubmit((formValues) => saveMutation.mutate(formValues))}
            >
              {VERIFICATION_FIELD_CONFIG.map((field) => {
                const status = deriveFieldStatus(
                  field.key,
                  values,
                  extraction,
                  propertyDetail.verified_property,
                );

                return (
                  <div
                    className="rounded-2xl border border-border/70 bg-background/80 p-4"
                    key={field.key}
                  >
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div>
                        <label
                          className="text-sm font-semibold text-foreground"
                          htmlFor={field.key}
                        >
                          {field.label}
                        </label>
                        <p className="mt-1 text-xs leading-5 text-muted-foreground">
                          {field.helperText}
                        </p>
                      </div>
                      <VerificationStatusBadge status={status} />
                    </div>
                    <Input
                      {...form.register(field.key)}
                      id={field.key}
                      inputMode={field.inputMode}
                      placeholder={field.placeholder}
                    />
                  </div>
                );
              })}
              <div className="md:col-span-2">
                {submissionError ? (
                  <div
                    aria-live="polite"
                    className="mb-4 rounded-2xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger"
                    role="alert"
                  >
                    {submissionError}
                  </div>
                ) : null}
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button size="lg" type="submit">
                    {saveMutation.isPending ? "Saving verification..." : "Save and continue"}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                  <Button
                    onClick={() =>
                      form.reset(
                        createFormValues(
                          propertyDetail.property,
                          propertyDetail.verified_property,
                        ),
                      )
                    }
                    type="button"
                    variant="outline"
                  >
                    <RefreshCcw className="mr-2 h-4 w-4" />
                    Reset values
                  </Button>
                </div>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Property summary</CardTitle>
              <CardDescription>
                Persisted property ID: <span className="font-medium text-foreground">{propertyId}</span>
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 text-sm">
              <SummaryRow label="Address" value={values.full_address || "Missing"} />
              <SummaryRow
                label="Asking price"
                value={formatCurrency(values.asking_price || null)}
              />
              <SummaryRow label="Provider" value={propertyDetail.provider} />
              <SummaryRow
                label="Latest analysis"
                value={propertyDetail.latest_analysis?.status ?? "No analyses yet"}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>What happens next</CardTitle>
              <CardDescription>
                After saving, the app will move to assumptions so the user can continue into
                analysis execution in the next phases.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>Verified snapshots stay immutable on historical analyses.</p>
              <p>Property edits update the current property record only.</p>
              <p>
                If you need to restart this demo flow, return to the <Link className="font-medium text-primary underline-offset-4 hover:underline" href="/">landing page</Link>.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>
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
  value: string;
}): React.JSX.Element {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-border/60 bg-background/70 p-3">
      <div className="text-muted-foreground">{label}</div>
      <div className="text-right font-medium text-foreground">{value}</div>
    </div>
  );
}
