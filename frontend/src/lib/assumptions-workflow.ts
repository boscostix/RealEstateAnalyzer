import type {
  AnalysisAssumptions,
  AnalysisPreset,
  FinancingType,
  PropertyDetail,
} from "@/lib/api/types";

export type AssumptionsFormValues = {
  purchase_price: string;
  preset: AnalysisPreset;
  financing_type: FinancingType;
  down_payment_amount: string;
  down_payment_percent: string;
  interest_rate_percent: string;
  loan_term_years: string;
  loan_amount: string;
  points: string;
  additional_lender_fees: string;
  monthly_mortgage_insurance: string;
  closing_costs: string;
  closing_cost_percent: string;
  lender_fees: string;
  repairs: string;
  initial_reserves: string;
  other_acquisition_costs: string;
  monthly_rent: string;
  other_monthly_income: string;
  vacancy_percent: string;
  annual_property_taxes: string;
  annual_insurance: string;
  annual_hoa: string;
  management_percent: string;
  maintenance_percent: string;
  maintenance_annual: string;
  capex_percent: string;
  capex_annual: string;
  leasing_fee_percent: string;
  tenant_turnover_frequency_years: string;
  turnover_cost: string;
  owner_paid_utilities_monthly: string;
  landscaping_monthly: string;
  pest_control_monthly: string;
  other_monthly_expenses: string;
  other_annual_expenses: string;
  holding_period_years: string;
  annual_rent_growth_percent: string;
  annual_expense_growth_percent: string;
  annual_appreciation_percent: string;
  selling_cost_percent: string;
  monthly_cash_flow: string;
  cap_rate_percent: string;
  cash_on_cash_percent: string;
  dscr: string;
};

export type AssumptionFieldConfig = {
  key: keyof AssumptionsFormValues;
  label: string;
  placeholder: string;
  helperText: string;
  inputMode?: React.HTMLAttributes<HTMLInputElement>["inputMode"];
};

export const PRESET_LABELS: Record<AnalysisPreset, string> = {
  conservative: "Conservative",
  standard: "Standard",
  aggressive: "Aggressive",
  custom: "Custom",
};

const PRESET_VALUES: Record<
  Exclude<AnalysisPreset, "custom">,
  Pick<
    AssumptionsFormValues,
    | "vacancy_percent"
    | "management_percent"
    | "maintenance_percent"
    | "capex_percent"
    | "annual_rent_growth_percent"
    | "annual_expense_growth_percent"
    | "annual_appreciation_percent"
    | "selling_cost_percent"
  >
> = {
  conservative: {
    vacancy_percent: "7",
    management_percent: "10",
    maintenance_percent: "7",
    capex_percent: "7",
    annual_rent_growth_percent: "1",
    annual_expense_growth_percent: "3",
    annual_appreciation_percent: "2",
    selling_cost_percent: "7",
  },
  standard: {
    vacancy_percent: "5",
    management_percent: "8",
    maintenance_percent: "5",
    capex_percent: "5",
    annual_rent_growth_percent: "2",
    annual_expense_growth_percent: "2",
    annual_appreciation_percent: "3",
    selling_cost_percent: "6",
  },
  aggressive: {
    vacancy_percent: "3",
    management_percent: "0",
    maintenance_percent: "4",
    capex_percent: "4",
    annual_rent_growth_percent: "3",
    annual_expense_growth_percent: "2",
    annual_appreciation_percent: "4",
    selling_cost_percent: "5",
  },
};

export const OVERVIEW_FIELDS: AssumptionFieldConfig[] = [
  {
    key: "purchase_price",
    label: "Purchase price",
    placeholder: "440000",
    helperText: "This should reflect the basis you want underwriting to use.",
    inputMode: "decimal",
  },
];

export const FINANCING_FIELDS: AssumptionFieldConfig[] = [
  {
    key: "down_payment_percent",
    label: "Down payment percent",
    placeholder: "20",
    helperText: "Use either down payment percent, down payment amount, or loan amount.",
    inputMode: "decimal",
  },
  {
    key: "down_payment_amount",
    label: "Down payment amount",
    placeholder: "88000",
    helperText: "Optional alternative to down payment percent.",
    inputMode: "decimal",
  },
  {
    key: "loan_amount",
    label: "Loan amount",
    placeholder: "352000",
    helperText: "Optional alternative if you want to set the financed balance directly.",
    inputMode: "decimal",
  },
  {
    key: "interest_rate_percent",
    label: "Interest rate percent",
    placeholder: "6.25",
    helperText: "Required for conventional financing.",
    inputMode: "decimal",
  },
  {
    key: "loan_term_years",
    label: "Loan term years",
    placeholder: "30",
    helperText: "Required for conventional financing.",
    inputMode: "numeric",
  },
  {
    key: "points",
    label: "Points",
    placeholder: "0",
    helperText: "Origination points as a percent of the loan amount.",
    inputMode: "decimal",
  },
  {
    key: "additional_lender_fees",
    label: "Additional lender fees",
    placeholder: "0",
    helperText: "Any extra financing fees beyond origination points.",
    inputMode: "decimal",
  },
  {
    key: "monthly_mortgage_insurance",
    label: "Monthly mortgage insurance",
    placeholder: "0",
    helperText: "Leave at zero if mortgage insurance does not apply.",
    inputMode: "decimal",
  },
];

export const ACQUISITION_FIELDS: AssumptionFieldConfig[] = [
  {
    key: "closing_costs",
    label: "Closing costs amount",
    placeholder: "0",
    helperText: "Use either a flat closing cost amount or a percent.",
    inputMode: "decimal",
  },
  {
    key: "closing_cost_percent",
    label: "Closing costs percent",
    placeholder: "0",
    helperText: "Optional alternative to entering flat closing costs.",
    inputMode: "decimal",
  },
  {
    key: "lender_fees",
    label: "Lender fees",
    placeholder: "0",
    helperText: "Base lender fees in addition to financing-specific fees.",
    inputMode: "decimal",
  },
  {
    key: "repairs",
    label: "Repairs",
    placeholder: "0",
    helperText: "Immediate make-ready or rehabilitation budget.",
    inputMode: "decimal",
  },
  {
    key: "initial_reserves",
    label: "Initial reserves",
    placeholder: "0",
    helperText: "Cash reserves set aside at acquisition.",
    inputMode: "decimal",
  },
  {
    key: "other_acquisition_costs",
    label: "Other acquisition costs",
    placeholder: "0",
    helperText: "Any remaining one-time closing or setup costs.",
    inputMode: "decimal",
  },
];

export const INCOME_FIELDS: AssumptionFieldConfig[] = [
  {
    key: "monthly_rent",
    label: "Monthly rent",
    placeholder: "3200",
    helperText: "Required income input for the first underwriting pass.",
    inputMode: "decimal",
  },
  {
    key: "other_monthly_income",
    label: "Other monthly income",
    placeholder: "0",
    helperText: "Laundry, parking, pet rent, storage, or similar items.",
    inputMode: "decimal",
  },
  {
    key: "vacancy_percent",
    label: "Vacancy percent",
    placeholder: "5",
    helperText: "Preset-driven by default, but still fully editable.",
    inputMode: "decimal",
  },
];

export const EXPENSE_FIELDS: AssumptionFieldConfig[] = [
  {
    key: "annual_property_taxes",
    label: "Annual property taxes",
    placeholder: "4200",
    helperText: "Required unless the verified property snapshot already provides taxes.",
    inputMode: "decimal",
  },
  {
    key: "annual_insurance",
    label: "Annual insurance",
    placeholder: "1800",
    helperText: "Required backend input.",
    inputMode: "decimal",
  },
  {
    key: "annual_hoa",
    label: "Annual HOA",
    placeholder: "0",
    helperText: "Required if the verified property snapshot does not already include it.",
    inputMode: "decimal",
  },
  {
    key: "management_percent",
    label: "Management percent",
    placeholder: "8",
    helperText: "Preset-driven by default.",
    inputMode: "decimal",
  },
  {
    key: "maintenance_percent",
    label: "Maintenance percent",
    placeholder: "5",
    helperText: "Optional percent-based maintenance assumption.",
    inputMode: "decimal",
  },
  {
    key: "maintenance_annual",
    label: "Maintenance annual",
    placeholder: "0",
    helperText: "Optional fixed-dollar maintenance alternative.",
    inputMode: "decimal",
  },
  {
    key: "capex_percent",
    label: "Capex percent",
    placeholder: "5",
    helperText: "Optional percent-based capex reserve assumption.",
    inputMode: "decimal",
  },
  {
    key: "capex_annual",
    label: "Capex annual",
    placeholder: "0",
    helperText: "Optional fixed-dollar capex reserve alternative.",
    inputMode: "decimal",
  },
  {
    key: "leasing_fee_percent",
    label: "Leasing fee percent",
    placeholder: "0",
    helperText: "Broker or leasing placement costs.",
    inputMode: "decimal",
  },
  {
    key: "tenant_turnover_frequency_years",
    label: "Turnover frequency years",
    placeholder: "1",
    helperText: "Average tenant turnover cadence.",
    inputMode: "decimal",
  },
  {
    key: "turnover_cost",
    label: "Turnover cost",
    placeholder: "0",
    helperText: "Cleaning, painting, or reletting cost per turnover.",
    inputMode: "decimal",
  },
  {
    key: "owner_paid_utilities_monthly",
    label: "Owner-paid utilities monthly",
    placeholder: "0",
    helperText: "Gas, water, sewer, trash, or electricity paid by owner.",
    inputMode: "decimal",
  },
  {
    key: "landscaping_monthly",
    label: "Landscaping monthly",
    placeholder: "0",
    helperText: "Recurring groundskeeping costs.",
    inputMode: "decimal",
  },
  {
    key: "pest_control_monthly",
    label: "Pest control monthly",
    placeholder: "0",
    helperText: "Recurring pest treatment allowance.",
    inputMode: "decimal",
  },
  {
    key: "other_monthly_expenses",
    label: "Other monthly expenses",
    placeholder: "0",
    helperText: "Any remaining recurring monthly operating costs.",
    inputMode: "decimal",
  },
  {
    key: "other_annual_expenses",
    label: "Other annual expenses",
    placeholder: "0",
    helperText: "Any remaining annual operating costs.",
    inputMode: "decimal",
  },
];

export const PROJECTION_FIELDS: AssumptionFieldConfig[] = [
  {
    key: "holding_period_years",
    label: "Holding period years",
    placeholder: "5",
    helperText: "Used for sale and projection calculations.",
    inputMode: "numeric",
  },
  {
    key: "annual_rent_growth_percent",
    label: "Annual rent growth percent",
    placeholder: "2",
    helperText: "Preset-driven by default.",
    inputMode: "decimal",
  },
  {
    key: "annual_expense_growth_percent",
    label: "Annual expense growth percent",
    placeholder: "2",
    helperText: "Preset-driven by default.",
    inputMode: "decimal",
  },
  {
    key: "annual_appreciation_percent",
    label: "Annual appreciation percent",
    placeholder: "3",
    helperText: "Preset-driven by default.",
    inputMode: "decimal",
  },
  {
    key: "selling_cost_percent",
    label: "Selling cost percent",
    placeholder: "6",
    helperText: "Preset-driven by default.",
    inputMode: "decimal",
  },
];

export const TARGET_FIELDS: AssumptionFieldConfig[] = [
  {
    key: "monthly_cash_flow",
    label: "Target monthly cash flow",
    placeholder: "0",
    helperText: "Optional target used for maximum-offer guidance.",
    inputMode: "decimal",
  },
  {
    key: "cap_rate_percent",
    label: "Target cap rate percent",
    placeholder: "0",
    helperText: "Optional investment hurdle.",
    inputMode: "decimal",
  },
  {
    key: "cash_on_cash_percent",
    label: "Target cash-on-cash percent",
    placeholder: "0",
    helperText: "Optional return hurdle.",
    inputMode: "decimal",
  },
  {
    key: "dscr",
    label: "Target DSCR",
    placeholder: "1.2",
    helperText: "Optional debt-service coverage hurdle.",
    inputMode: "decimal",
  },
];

export function createAssumptionsDefaults(property: PropertyDetail): AssumptionsFormValues {
  return {
    purchase_price: valueOrFallback(property.verified_property?.asking_price.final_value, ""),
    preset: "standard",
    financing_type: "conventional",
    down_payment_amount: "",
    down_payment_percent: "20",
    interest_rate_percent: "6.25",
    loan_term_years: "30",
    loan_amount: "",
    points: "0",
    additional_lender_fees: "0",
    monthly_mortgage_insurance: "0",
    closing_costs: "",
    closing_cost_percent: "",
    lender_fees: "0",
    repairs: "0",
    initial_reserves: "0",
    other_acquisition_costs: "0",
    monthly_rent: valueOrFallback(property.property?.estimated_monthly_rent, ""),
    other_monthly_income: "0",
    vacancy_percent: "5",
    annual_property_taxes: valueOrFallback(
      property.verified_property?.annual_property_tax.final_value,
      "",
    ),
    annual_insurance: "1800",
    annual_hoa: valueOrFallback(property.verified_property?.annual_hoa.final_value, ""),
    management_percent: "8",
    maintenance_percent: "5",
    maintenance_annual: "",
    capex_percent: "5",
    capex_annual: "",
    leasing_fee_percent: "0",
    tenant_turnover_frequency_years: "1",
    turnover_cost: "0",
    owner_paid_utilities_monthly: "0",
    landscaping_monthly: "0",
    pest_control_monthly: "0",
    other_monthly_expenses: "0",
    other_annual_expenses: "0",
    holding_period_years: "5",
    annual_rent_growth_percent: "2",
    annual_expense_growth_percent: "2",
    annual_appreciation_percent: "3",
    selling_cost_percent: "6",
    monthly_cash_flow: "",
    cap_rate_percent: "",
    cash_on_cash_percent: "",
    dscr: "",
  };
}

export function applyPreset(
  values: AssumptionsFormValues,
  preset: AnalysisPreset,
): AssumptionsFormValues {
  if (preset === "custom") {
    return {
      ...values,
      preset,
    };
  }

  return {
    ...values,
    preset,
    ...PRESET_VALUES[preset],
  };
}

export function serializeAssumptions(values: AssumptionsFormValues): AnalysisAssumptions {
  return {
    purchase_price: requiredDecimal(values.purchase_price),
    preset: values.preset,
    financing: {
      type: values.financing_type,
      down_payment_amount: nullableDecimal(values.down_payment_amount),
      down_payment_percent: nullableDecimal(values.down_payment_percent),
      interest_rate_percent:
        values.financing_type === "cash" ? null : nullableDecimal(values.interest_rate_percent),
      loan_term_years: values.financing_type === "cash" ? null : nullableInteger(values.loan_term_years),
      loan_amount: nullableDecimal(values.loan_amount),
      points: requiredDecimal(values.points),
      additional_lender_fees: requiredDecimal(values.additional_lender_fees),
      monthly_mortgage_insurance: requiredDecimal(values.monthly_mortgage_insurance),
    },
    acquisition: {
      closing_costs: nullableDecimal(values.closing_costs),
      closing_cost_percent: nullableDecimal(values.closing_cost_percent),
      lender_fees: requiredDecimal(values.lender_fees),
      repairs: requiredDecimal(values.repairs),
      initial_reserves: requiredDecimal(values.initial_reserves),
      other_acquisition_costs: requiredDecimal(values.other_acquisition_costs),
    },
    income: {
      monthly_rent: requiredDecimal(values.monthly_rent),
      other_monthly_income: requiredDecimal(values.other_monthly_income),
      vacancy_percent: requiredDecimal(values.vacancy_percent),
    },
    expenses: {
      annual_property_taxes: nullableDecimal(values.annual_property_taxes),
      annual_insurance: requiredDecimal(values.annual_insurance),
      annual_hoa: nullableDecimal(values.annual_hoa),
      management_percent: requiredDecimal(values.management_percent),
      maintenance_percent: nullableDecimal(values.maintenance_percent),
      maintenance_annual: nullableDecimal(values.maintenance_annual),
      capex_percent: nullableDecimal(values.capex_percent),
      capex_annual: nullableDecimal(values.capex_annual),
      leasing_fee_percent: requiredDecimal(values.leasing_fee_percent),
      tenant_turnover_frequency_years: requiredDecimal(values.tenant_turnover_frequency_years),
      turnover_cost: requiredDecimal(values.turnover_cost),
      owner_paid_utilities_monthly: requiredDecimal(values.owner_paid_utilities_monthly),
      landscaping_monthly: requiredDecimal(values.landscaping_monthly),
      pest_control_monthly: requiredDecimal(values.pest_control_monthly),
      other_monthly_expenses: requiredDecimal(values.other_monthly_expenses),
      other_annual_expenses: requiredDecimal(values.other_annual_expenses),
    },
    projections: {
      holding_period_years: requiredInteger(values.holding_period_years),
      annual_rent_growth_percent: requiredDecimal(values.annual_rent_growth_percent),
      annual_expense_growth_percent: requiredDecimal(values.annual_expense_growth_percent),
      annual_appreciation_percent: requiredDecimal(values.annual_appreciation_percent),
      selling_cost_percent: requiredDecimal(values.selling_cost_percent),
    },
    targets: {
      monthly_cash_flow: nullableDecimal(values.monthly_cash_flow),
      cap_rate_percent: nullableDecimal(values.cap_rate_percent),
      cash_on_cash_percent: nullableDecimal(values.cash_on_cash_percent),
      dscr: nullableDecimal(values.dscr),
    },
  };
}

function valueOrFallback(value: unknown, fallback: string): string {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  return String(value);
}

function nullableDecimal(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function nullableInteger(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed === "") {
    return null;
  }

  return Number(trimmed);
}

function requiredDecimal(value: string): string {
  return value.trim();
}

function requiredInteger(value: string): number {
  return Number(value.trim());
}
