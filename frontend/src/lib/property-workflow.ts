import type {
  NormalizedProperty,
  PropertyExtractionPayload,
  VerifiedPropertySnapshot,
  VerificationStatus,
} from "@/lib/api/types";

export const VERIFICATION_FIELDS = [
  "full_address",
  "asking_price",
  "bedrooms",
  "bathrooms",
  "square_feet",
  "lot_square_feet",
  "year_built",
  "annual_property_tax",
  "annual_hoa",
  "property_type",
] as const;

export type VerificationFieldKey = (typeof VERIFICATION_FIELDS)[number];

export type PropertyFormValues = Record<VerificationFieldKey, string>;

export type VerificationFieldConfig = {
  key: VerificationFieldKey;
  label: string;
  inputMode?: React.HTMLAttributes<HTMLInputElement>["inputMode"];
  placeholder: string;
  helperText: string;
};

export const VERIFICATION_FIELD_CONFIG: VerificationFieldConfig[] = [
  {
    key: "full_address",
    label: "Full address",
    placeholder: "123 Main St, Austin, TX 78701",
    helperText: "Use the complete street address the analyst should rely on.",
  },
  {
    key: "asking_price",
    label: "Asking price",
    inputMode: "decimal",
    placeholder: "479990",
    helperText: "Enter the current listing price before assumptions are applied.",
  },
  {
    key: "bedrooms",
    label: "Bedrooms",
    inputMode: "decimal",
    placeholder: "3",
    helperText: "Fractions are allowed when the source provides them.",
  },
  {
    key: "bathrooms",
    label: "Bathrooms",
    inputMode: "decimal",
    placeholder: "2.5",
    helperText: "Use the total baths value shown in the listing.",
  },
  {
    key: "square_feet",
    label: "Interior square feet",
    inputMode: "numeric",
    placeholder: "1820",
    helperText: "Living area is used downstream in underwriting and rent analysis.",
  },
  {
    key: "lot_square_feet",
    label: "Lot square feet",
    inputMode: "numeric",
    placeholder: "7200",
    helperText: "Leave blank if the listing does not disclose lot size.",
  },
  {
    key: "year_built",
    label: "Year built",
    inputMode: "numeric",
    placeholder: "1998",
    helperText: "This is helpful for capex and condition review later in the flow.",
  },
  {
    key: "annual_property_tax",
    label: "Annual property tax",
    inputMode: "decimal",
    placeholder: "6400",
    helperText: "Use annualized tax dollars whenever the listing includes them.",
  },
  {
    key: "annual_hoa",
    label: "Annual HOA",
    inputMode: "decimal",
    placeholder: "1200",
    helperText: "Enter zero only when the property truly has no HOA dues.",
  },
  {
    key: "property_type",
    label: "Property type",
    placeholder: "Single Family",
    helperText: "Examples: Single Family, Condo, Townhouse, Duplex.",
  },
];

const STORAGE_PREFIX = "listing-extraction:";

const NUMERIC_FIELDS = new Set<VerificationFieldKey>([
  "asking_price",
  "bedrooms",
  "bathrooms",
  "square_feet",
  "lot_square_feet",
  "year_built",
  "annual_property_tax",
  "annual_hoa",
]);

export function createFormValues(
  property: NormalizedProperty | null | undefined,
  verifiedProperty?: VerifiedPropertySnapshot | null,
): PropertyFormValues {
  return {
    full_address:
      stringifyField(verifiedProperty?.full_address.final_value) ??
      stringifyField(property?.address?.full_address) ??
      "",
    asking_price:
      stringifyField(verifiedProperty?.asking_price.final_value) ??
      stringifyField(property?.asking_price) ??
      "",
    bedrooms:
      stringifyField(verifiedProperty?.bedrooms.final_value) ??
      stringifyField(property?.bedrooms) ??
      "",
    bathrooms:
      stringifyField(verifiedProperty?.bathrooms.final_value) ??
      stringifyField(property?.bathrooms) ??
      "",
    square_feet:
      stringifyField(verifiedProperty?.square_feet.final_value) ??
      stringifyField(property?.square_feet) ??
      "",
    lot_square_feet:
      stringifyField(verifiedProperty?.lot_square_feet.final_value) ??
      stringifyField(property?.lot_square_feet) ??
      "",
    year_built:
      stringifyField(verifiedProperty?.year_built.final_value) ??
      stringifyField(property?.year_built) ??
      "",
    annual_property_tax:
      stringifyField(verifiedProperty?.annual_property_tax.final_value) ??
      stringifyField(property?.annual_property_tax) ??
      "",
    annual_hoa:
      stringifyField(verifiedProperty?.annual_hoa.final_value) ??
      stringifyField(property?.annual_hoa) ??
      "",
    property_type:
      stringifyField(verifiedProperty?.property_type.final_value) ??
      stringifyField(property?.property_type) ??
      "",
  };
}

export function buildVerificationRequest(
  extraction: PropertyExtractionPayload,
  values: PropertyFormValues,
): {
  corrections: Record<string, string | number>;
  confirmed_fields: string[];
} {
  const corrections: Record<string, string | number> = {};
  const confirmedFields: string[] = [];

  for (const key of VERIFICATION_FIELDS) {
    const trimmed = values[key].trim();
    const extractedValue = extractionFieldValue(extraction.property, key);
    const extractedNormalized = normalizeValue(extractedValue);
    const currentNormalized = normalizeFormValue(key, trimmed);

    if (trimmed === "") {
      continue;
    }

    if (extractedNormalized === undefined) {
      corrections[key] = currentNormalized;
      continue;
    }

    if (currentNormalized === extractedNormalized) {
      confirmedFields.push(key);
      continue;
    }

    corrections[key] = currentNormalized;
  }

  return {
    corrections,
    confirmed_fields: confirmedFields,
  };
}

export function buildUpdatedProperty(
  baseProperty: NormalizedProperty,
  values: PropertyFormValues,
): NormalizedProperty {
  return {
    ...baseProperty,
    address: {
      ...baseProperty.address,
      full_address: emptyToNull(values.full_address),
    },
    asking_price: parseNumericValue("asking_price", values.asking_price),
    bedrooms: parseNumericValue("bedrooms", values.bedrooms),
    bathrooms: parseNumericValue("bathrooms", values.bathrooms),
    square_feet: parseIntegerValue(values.square_feet),
    lot_square_feet: parseIntegerValue(values.lot_square_feet),
    year_built: parseIntegerValue(values.year_built),
    annual_property_tax: parseNumericValue("annual_property_tax", values.annual_property_tax),
    annual_hoa: parseNumericValue("annual_hoa", values.annual_hoa),
    property_type: emptyToNull(values.property_type),
  };
}

export function deriveFieldStatus(
  key: VerificationFieldKey,
  values: PropertyFormValues,
  extraction: PropertyExtractionPayload,
  verifiedProperty?: VerifiedPropertySnapshot | null,
): VerificationStatus {
  const existingStatus = verifiedProperty?.[key]?.status;
  const extractedValue = extractionFieldValue(extraction.property, key);
  const currentValue = values[key].trim();

  if (currentValue === "") {
    return "missing";
  }

  const normalizedCurrent = normalizeFormValue(key, currentValue);
  const normalizedExtracted = normalizeValue(extractedValue);

  if (normalizedExtracted === undefined) {
    return existingStatus === "verified" ? "verified" : "corrected";
  }

  if (normalizedCurrent === normalizedExtracted) {
    return existingStatus ?? "unverified";
  }

  return "corrected";
}

export function verificationStatusTone(
  status: VerificationStatus,
): "success" | "warning" | "danger" | "neutral" {
  switch (status) {
    case "verified":
      return "success";
    case "corrected":
    case "estimated":
      return "warning";
    case "missing":
    case "conflicting":
      return "danger";
    case "unverified":
    default:
      return "neutral";
  }
}

export function saveExtractionForProperty(
  propertyId: string,
  extraction: PropertyExtractionPayload,
): void {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(`${STORAGE_PREFIX}${propertyId}`, JSON.stringify(extraction));
}

export function loadExtractionForProperty(
  propertyId: string,
): PropertyExtractionPayload | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.sessionStorage.getItem(`${STORAGE_PREFIX}${propertyId}`);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as PropertyExtractionPayload;
  } catch {
    return null;
  }
}

function stringifyField(value: unknown): string | undefined {
  if (value === null || value === undefined) {
    return undefined;
  }

  return String(value);
}

function extractionFieldValue(
  property: NormalizedProperty,
  key: VerificationFieldKey,
): string | number | null | undefined {
  if (key === "full_address") {
    return property.address?.full_address;
  }

  return property[key] as string | number | null | undefined;
}

function normalizeFormValue(key: VerificationFieldKey, value: string): string | number {
  if (!NUMERIC_FIELDS.has(key)) {
    return value;
  }

  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : value;
}

function normalizeValue(value: unknown): string | number | undefined {
  if (value === null || value === undefined || value === "") {
    return undefined;
  }

  if (typeof value === "number") {
    return value;
  }

  const numeric = Number(value);
  if (Number.isFinite(numeric) && String(value).trim() !== "") {
    return numeric;
  }

  return String(value);
}

function parseNumericValue(
  key: VerificationFieldKey,
  value: string,
): number | string | null {
  const trimmed = value.trim();
  if (trimmed === "") {
    return null;
  }

  return normalizeFormValue(key, trimmed);
}

function parseIntegerValue(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed === "") {
    return null;
  }

  const numeric = Number(trimmed);
  return Number.isFinite(numeric) ? Math.trunc(numeric) : null;
}

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}
