"use client";

import { useRouter, useParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { ErrorState } from "@/components/common/error-state";
import { PageLoadingState } from "@/components/common/page-loading-state";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createAnalysis } from "@/lib/api/analyses";
import type { ApiClientError } from "@/lib/api/client";
import { getProperty } from "@/lib/api/properties";
import {
  ACQUISITION_FIELDS,
  applyPreset,
  createAssumptionsDefaults,
  EXPENSE_FIELDS,
  FINANCING_FIELDS,
  INCOME_FIELDS,
  OVERVIEW_FIELDS,
  PRESET_LABELS,
  PROJECTION_FIELDS,
  serializeAssumptions,
  TARGET_FIELDS,
  type AssumptionFieldConfig,
  type AssumptionsFormValues,
} from "@/lib/assumptions-workflow";
import { formatCurrency } from "@/lib/formatters";
import { cn } from "@/lib/utils";

const numericString = z
  .string()
  .refine((value) => value.trim() === "" || !Number.isNaN(Number(value)), "Enter a valid number.");

const assumptionsSchema = z
  .object({
    purchase_price: z.string().min(1, "Purchase price is required."),
    preset: z.enum(["conservative", "standard", "aggressive", "custom"]),
    financing_type: z.enum(["conventional", "cash"]),
    down_payment_amount: numericString,
    down_payment_percent: numericString,
    interest_rate_percent: numericString,
    loan_term_years: numericString,
    loan_amount: numericString,
    points: numericString,
    additional_lender_fees: numericString,
    monthly_mortgage_insurance: numericString,
    closing_costs: numericString,
    closing_cost_percent: numericString,
    lender_fees: numericString,
    repairs: numericString,
    initial_reserves: numericString,
    other_acquisition_costs: numericString,
    monthly_rent: z.string().min(1, "Monthly rent is required."),
    other_monthly_income: numericString,
    vacancy_percent: z.string().min(1, "Vacancy percent is required."),
    annual_property_taxes: numericString,
    annual_insurance: z.string().min(1, "Annual insurance is required."),
    annual_hoa: numericString,
    management_percent: z.string().min(1, "Management percent is required."),
    maintenance_percent: numericString,
    maintenance_annual: numericString,
    capex_percent: numericString,
    capex_annual: numericString,
    leasing_fee_percent: numericString,
    tenant_turnover_frequency_years: numericString,
    turnover_cost: numericString,
    owner_paid_utilities_monthly: numericString,
    landscaping_monthly: numericString,
    pest_control_monthly: numericString,
    other_monthly_expenses: numericString,
    other_annual_expenses: numericString,
    holding_period_years: z.string().min(1, "Holding period is required."),
    annual_rent_growth_percent: z.string().min(1, "Rent growth is required."),
    annual_expense_growth_percent: z.string().min(1, "Expense growth is required."),
    annual_appreciation_percent: z.string().min(1, "Appreciation is required."),
    selling_cost_percent: z.string().min(1, "Selling cost is required."),
    monthly_cash_flow: numericString,
    cap_rate_percent: numericString,
    cash_on_cash_percent: numericString,
    dscr: numericString,
  })
  .superRefine((values, context) => {
    if (Number(values.purchase_price) <= 0) {
      context.addIssue({
        code: "custom",
        message: "Purchase price must be greater than zero.",
        path: ["purchase_price"],
      });
    }

    if (Number(values.monthly_rent) < 0) {
      context.addIssue({
        code: "custom",
        message: "Monthly rent cannot be negative.",
        path: ["monthly_rent"],
      });
    }

    if (Number(values.annual_insurance) < 0) {
      context.addIssue({
        code: "custom",
        message: "Annual insurance cannot be negative.",
        path: ["annual_insurance"],
      });
    }

    if (values.financing_type === "conventional") {
      if (
        values.down_payment_amount.trim() === "" &&
        values.down_payment_percent.trim() === "" &&
        values.loan_amount.trim() === ""
      ) {
        context.addIssue({
          code: "custom",
          message: "Provide a down payment percent, down payment amount, or loan amount.",
          path: ["down_payment_percent"],
        });
      }
      if (values.interest_rate_percent.trim() === "") {
        context.addIssue({
          code: "custom",
          message: "Interest rate is required for financed purchases.",
          path: ["interest_rate_percent"],
        });
      } else if (Number(values.interest_rate_percent) < 0) {
        context.addIssue({
          code: "custom",
          message: "Interest rate cannot be negative.",
          path: ["interest_rate_percent"],
        });
      }
      if (values.loan_term_years.trim() === "") {
        context.addIssue({
          code: "custom",
          message: "Loan term is required for financed purchases.",
          path: ["loan_term_years"],
        });
      } else if (Number(values.loan_term_years) <= 0) {
        context.addIssue({
          code: "custom",
          message: "Loan term must be positive.",
          path: ["loan_term_years"],
        });
      }
      if (
        values.loan_amount.trim() !== "" &&
        values.down_payment_amount.trim() !== ""
      ) {
        context.addIssue({
          code: "custom",
          message: "Provide either down payment amount or loan amount, not both.",
          path: ["loan_amount"],
        });
      }
    }
  });

export function AssumptionsFlow(): React.JSX.Element {
  const params = useParams<{ propertyId: string }>();
  const router = useRouter();
  const propertyId = params.propertyId;
  const propertyQuery = useQuery({
    queryKey: ["property", propertyId],
    queryFn: () => getProperty(propertyId),
  });
  const form = useForm<AssumptionsFormValues>({
    resolver: zodResolver(assumptionsSchema),
    defaultValues: undefined,
  });

  useEffect(() => {
    if (propertyQuery.data?.property) {
      form.reset(createAssumptionsDefaults(propertyQuery.data.property));
    }
  }, [form, propertyQuery.data]);

  const createMutation = useMutation({
    mutationFn: async (values: AssumptionsFormValues) => {
      return createAnalysis(propertyId, {
        assumptions: serializeAssumptions(values),
      });
    },
    onSuccess: (response) => {
      router.push(`/analyses/${response.analysis.id}`);
    },
  });
  const financingType = useWatch({
    control: form.control,
    name: "financing_type",
  });
  const preset = useWatch({
    control: form.control,
    name: "preset",
  });

  if (propertyQuery.isPending) {
    return <PageLoadingState description="Preparing the property context for underwriting assumptions." title="Loading assumptions" />;
  }

  if (propertyQuery.error) {
    return (
      <ErrorState
        message={mutationMessage(propertyQuery.error) ?? "Unable to load the property."}
      />
    );
  }

  const property = propertyQuery.data?.property;
  if (!property?.verified_property) {
    return (
      <ErrorState
        title="Verified property missing"
        message="This workflow needs a verified property snapshot before assumptions can be collected."
      />
    );
  }

  const submissionError = mutationMessage(createMutation.error);

  return (
    <div className="grid gap-8">
      <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader className="gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge tone="success">Assumptions</StatusBadge>
              <StatusBadge tone="neutral">{`${PRESET_LABELS[preset || "standard"]} preset`}</StatusBadge>
            </div>
            <div className="space-y-2">
              <CardTitle className="text-3xl">Set underwriting assumptions and start the analysis.</CardTitle>
              <CardDescription className="max-w-2xl text-base leading-7">
                The form mirrors the backend assumptions model directly, including financing,
                acquisition, income, expenses, projections, and targets. Presets update the same
                grouped fields the underwriting service uses.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <form
              className="grid gap-6"
              onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}
            >
              <section className="grid gap-4">
                <FormSectionHeader
                  description="Choose a preset, then tune the assumptions the analysis should use."
                  title="Overview"
                />
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-border/70 bg-background/80 p-4">
                    <label className="text-sm font-semibold text-foreground" htmlFor="preset">
                      Preset
                    </label>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">
                      Presets update vacancy, management, maintenance, capex, and projection growth assumptions.
                    </p>
                    <select
                      className={selectClassName}
                      id="preset"
                      value={preset || "standard"}
                      onChange={(event) => {
                        const nextValues = applyPreset(
                          {
                            ...form.getValues(),
                            preset: event.target.value as AssumptionsFormValues["preset"],
                          },
                          event.target.value as AssumptionsFormValues["preset"],
                        );
                        form.reset(nextValues, {
                          keepErrors: true,
                          keepDirty: true,
                          keepTouched: true,
                        });
                      }}
                    >
                      {Object.entries(PRESET_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-background/80 p-4">
                    <label className="text-sm font-semibold text-foreground" htmlFor="financing_type">
                      Financing type
                    </label>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">
                      Switching to cash removes the need for interest rate and loan term inputs.
                    </p>
                    <select className={selectClassName} id="financing_type" {...form.register("financing_type")}>
                      <option value="conventional">Conventional</option>
                      <option value="cash">Cash</option>
                    </select>
                  </div>
                </div>
                <FieldGrid fields={OVERVIEW_FIELDS} form={form} />
              </section>

              <AssumptionSection
                fields={FINANCING_FIELDS}
                form={form}
                muted={financingType === "cash"}
                title="Financing"
              />
              <AssumptionSection fields={ACQUISITION_FIELDS} form={form} title="Acquisition" />
              <AssumptionSection fields={INCOME_FIELDS} form={form} title="Income" />
              <AssumptionSection fields={EXPENSE_FIELDS} form={form} title="Expenses" />
              <AssumptionSection fields={PROJECTION_FIELDS} form={form} title="Projections" />
              <AssumptionSection fields={TARGET_FIELDS} form={form} title="Targets" />

              {submissionError ? (
                <div className="rounded-2xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger">
                  {submissionError}
                </div>
              ) : null}

              <div className="flex flex-col gap-3 sm:flex-row">
                <Button size="lg" type="submit">
                  {createMutation.isPending ? "Starting analysis..." : "Start analysis"}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
                <Button
                  onClick={() => form.reset(createAssumptionsDefaults(property))}
                  type="button"
                  variant="outline"
                >
                  Reset assumptions
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Property context</CardTitle>
              <CardDescription>
                Assumptions will be attached to the verified property snapshot already stored on this record.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 text-sm">
              <SummaryRow label="Property ID" value={property.id} />
              <SummaryRow label="Address" value={property.full_address || "Missing"} />
              <SummaryRow
                label="Verified asking price"
                value={formatCurrency(property.verified_property.asking_price.final_value ?? null)}
              />
              <SummaryRow
                label="Verified annual taxes"
                value={formatCurrency(property.verified_property.annual_property_tax.final_value ?? null)}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>What happens next</CardTitle>
              <CardDescription>
                Starting analysis creates a stable analysis ID, saves the assumptions snapshot, and hands the record to the background execution service.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>Backend validation still runs and any structured API error is shown here.</p>
              <p>The next page polls analysis status using the stable analysis ID.</p>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}

function AssumptionSection({
  title,
  fields,
  form,
  muted = false,
}: {
  title: string;
  fields: AssumptionFieldConfig[];
  form: ReturnType<typeof useForm<AssumptionsFormValues>>;
  muted?: boolean;
}): React.JSX.Element {
  return (
    <section className="grid gap-4">
      <FormSectionHeader
        description={`Edit the ${title.toLowerCase()} assumptions that will be persisted with this analysis.`}
        title={title}
      />
      <div className={cn("grid gap-4 md:grid-cols-2", muted && "opacity-70")}>
        <FieldGrid fields={fields} form={form} />
      </div>
    </section>
  );
}

function FieldGrid({
  fields,
  form,
}: {
  fields: AssumptionFieldConfig[];
  form: ReturnType<typeof useForm<AssumptionsFormValues>>;
}): React.JSX.Element {
  return (
    <>
      {fields.map((field) => {
        const error = form.formState.errors[field.key];
        return (
          <div className="rounded-2xl border border-border/70 bg-background/80 p-4" key={field.key}>
            <label className="text-sm font-semibold text-foreground" htmlFor={field.key}>
              {field.label}
            </label>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{field.helperText}</p>
            <Input
              className="mt-3"
              id={field.key}
              inputMode={field.inputMode}
              placeholder={field.placeholder}
              {...form.register(field.key)}
            />
            {error ? <p className="mt-2 text-xs text-danger">{error.message}</p> : null}
          </div>
        );
      })}
    </>
  );
}

function FormSectionHeader({
  title,
  description,
}: {
  title: string;
  description: string;
}): React.JSX.Element {
  return (
    <div>
      <div className="text-lg font-semibold text-foreground">{title}</div>
      <p className="text-sm text-muted-foreground">{description}</p>
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

const selectClassName =
  "mt-3 flex h-11 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground outline-none ring-offset-background transition focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2";
