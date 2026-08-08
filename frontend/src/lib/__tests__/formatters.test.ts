import {
  formatCurrency,
  formatMonthlyCurrency,
  formatPercent,
  formatShortDate,
} from "@/lib/formatters";

describe("formatters", () => {
  it("formats money and percentages consistently", () => {
    expect(formatCurrency("479990")).toBe("$479,990");
    expect(formatMonthlyCurrency(3200)).toBe("$3,200/mo");
    expect(formatPercent("7.3")).toBe("7.3%");
  });

  it("returns fallback text for missing values", () => {
    expect(formatCurrency(null)).toBe("N/A");
    expect(formatPercent(undefined)).toBe("N/A");
  });

  it("formats short dates", () => {
    expect(formatShortDate("2026-08-08")).toBe("Aug 8, 2026");
  });
});
