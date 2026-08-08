import {
  applyPreset,
  createAssumptionsDefaults,
  serializeAssumptions,
} from "@/lib/assumptions-workflow";
import type { PropertyDetail } from "@/lib/api/types";

const property: PropertyDetail = {
  id: "prop-123",
  source_url: "https://www.zillow.com/homedetails/example",
  provider: "zillow",
  full_address: "123 Main St, Dallas, TX 75001",
  created_at: "2026-08-08T12:00:00Z",
  updated_at: "2026-08-08T12:00:00Z",
  current_version: 2,
  analysis_count: 0,
  property: {
    source_url: "https://www.zillow.com/homedetails/example",
    provider: "zillow",
    estimated_monthly_rent: "3200",
  },
  verified_property: {
    source_url: "https://www.zillow.com/homedetails/example",
    provider: "zillow",
    full_address: { status: "verified", final_value: "123 Main St, Dallas, TX 75001" },
    asking_price: { status: "verified", final_value: "445000" },
    bedrooms: { status: "verified", final_value: "3" },
    bathrooms: { status: "verified", final_value: "2" },
    square_feet: { status: "verified", final_value: 1800 },
    lot_square_feet: { status: "verified", final_value: 7200 },
    year_built: { status: "verified", final_value: 1999 },
    annual_property_tax: { status: "verified", final_value: "4200" },
    annual_hoa: { status: "verified", final_value: "0" },
    property_type: { status: "verified", final_value: "single_family" },
  },
};

describe("assumptions workflow", () => {
  it("builds defaults from the current property snapshot", () => {
    const defaults = createAssumptionsDefaults(property);

    expect(defaults.purchase_price).toBe("445000");
    expect(defaults.monthly_rent).toBe("3200");
    expect(defaults.annual_property_taxes).toBe("4200");
    expect(defaults.annual_hoa).toBe("0");
    expect(defaults.preset).toBe("standard");
  });

  it("applies backend-aligned preset values", () => {
    const conservative = applyPreset(createAssumptionsDefaults(property), "conservative");

    expect(conservative.vacancy_percent).toBe("7");
    expect(conservative.management_percent).toBe("10");
    expect(conservative.maintenance_percent).toBe("7");
    expect(conservative.annual_rent_growth_percent).toBe("1");
  });

  it("serializes form values into the persisted analysis request payload", () => {
    const payload = serializeAssumptions({
      ...createAssumptionsDefaults(property),
      preset: "custom",
      purchase_price: "440000",
      annual_insurance: "1800",
      monthly_cash_flow: "250",
      dscr: "1.2",
      closing_costs: "",
      closing_cost_percent: "2",
    });

    expect(payload).toMatchObject({
      purchase_price: "440000",
      preset: "custom",
      financing: {
        type: "conventional",
        down_payment_percent: "20",
        interest_rate_percent: "6.25",
        loan_term_years: 30,
      },
      acquisition: {
        closing_costs: null,
        closing_cost_percent: "2",
      },
      targets: {
        monthly_cash_flow: "250",
        dscr: "1.2",
      },
    });
  });
});
