import {
  buildUpdatedProperty,
  buildVerificationRequest,
  createFormValues,
  deriveFieldStatus,
  loadExtractionForProperty,
  saveExtractionForProperty,
} from "@/lib/property-workflow";
import type {
  NormalizedProperty,
  PropertyExtractionPayload,
  VerifiedPropertySnapshot,
} from "@/lib/api/types";

const property: NormalizedProperty = {
  source_url: "https://www.zillow.com/homedetails/example",
  provider: "zillow",
  address: {
    full_address: "123 Main St, Austin, TX 78701",
  },
  asking_price: "479990",
  bedrooms: "3",
  bathrooms: "2",
  square_feet: 1800,
  lot_square_feet: null,
  year_built: 1999,
  annual_property_tax: null,
  annual_hoa: "1200",
  property_type: "Single Family",
};

const extraction: PropertyExtractionPayload = {
  provider: "zillow",
  source_url: "https://www.zillow.com/homedetails/example",
  property,
  metadata: {
    extraction_method: "next_data",
    retrieved_at: "2026-08-08T12:00:00Z",
    fields_found: 7,
    fields_missing: ["lot_square_feet", "annual_property_tax"],
    warnings: [],
  },
  field_provenance: {
    asking_price: {
      value: "479990",
      source: "next_data",
      confidence: 0.98,
      raw_value: "$479,990",
    },
  },
};

const verifiedProperty: VerifiedPropertySnapshot = {
  source_url: extraction.source_url,
  provider: extraction.provider,
  full_address: { final_value: property.address?.full_address, status: "verified" },
  asking_price: { final_value: property.asking_price, status: "verified" },
  bedrooms: { final_value: property.bedrooms, status: "verified" },
  bathrooms: { final_value: property.bathrooms, status: "verified" },
  square_feet: { final_value: property.square_feet, status: "verified" },
  lot_square_feet: { final_value: null, status: "missing" },
  year_built: { final_value: property.year_built, status: "verified" },
  annual_property_tax: { final_value: null, status: "missing" },
  annual_hoa: { final_value: property.annual_hoa, status: "verified" },
  property_type: { final_value: property.property_type, status: "verified" },
};

describe("property workflow helpers", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("prefills form values from verified data when present", () => {
    expect(createFormValues(property, verifiedProperty)).toMatchObject({
      full_address: "123 Main St, Austin, TX 78701",
      asking_price: "479990",
      lot_square_feet: "",
    });
  });

  it("builds corrections and confirmed fields from form values", () => {
    const request = buildVerificationRequest(extraction, {
      full_address: "123 Main St, Austin, TX 78701",
      asking_price: "485000",
      bedrooms: "3",
      bathrooms: "2",
      square_feet: "1800",
      lot_square_feet: "7200",
      year_built: "1999",
      annual_property_tax: "6400",
      annual_hoa: "1200",
      property_type: "Single Family",
    });

    expect(request.confirmed_fields).toEqual([
      "full_address",
      "bedrooms",
      "bathrooms",
      "square_feet",
      "year_built",
      "annual_hoa",
      "property_type",
    ]);
    expect(request.corrections).toMatchObject({
      asking_price: 485000,
      lot_square_feet: 7200,
      annual_property_tax: 6400,
    });
  });

  it("derives corrected and missing statuses for the editor", () => {
    const correctedStatus = deriveFieldStatus(
      "asking_price",
      {
        ...createFormValues(property),
        asking_price: "500000",
      },
      extraction,
    );
    const missingStatus = deriveFieldStatus(
      "annual_property_tax",
      {
        ...createFormValues(property),
        annual_property_tax: "",
      },
      extraction,
    );

    expect(correctedStatus).toBe("corrected");
    expect(missingStatus).toBe("missing");
  });

  it("builds a normalized property update payload", () => {
    const updated = buildUpdatedProperty(property, {
      full_address: "125 Main St, Austin, TX 78701",
      asking_price: "485000",
      bedrooms: "3",
      bathrooms: "2.5",
      square_feet: "1825",
      lot_square_feet: "7200",
      year_built: "2000",
      annual_property_tax: "6400",
      annual_hoa: "",
      property_type: "Townhouse",
    });

    expect(updated.address?.full_address).toBe("125 Main St, Austin, TX 78701");
    expect(updated.asking_price).toBe(485000);
    expect(updated.bathrooms).toBe(2.5);
    expect(updated.lot_square_feet).toBe(7200);
    expect(updated.annual_hoa).toBeNull();
    expect(updated.property_type).toBe("Townhouse");
  });

  it("stores extraction context in session storage", () => {
    saveExtractionForProperty("prop-123", extraction);

    expect(loadExtractionForProperty("prop-123")).toEqual(extraction);
  });
});
