const usdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatCurrency(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }

  const numeric = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(numeric)) {
    return "N/A";
  }

  return usdFormatter.format(numeric);
}

export function formatMonthlyCurrency(value: number | string | null | undefined): string {
  const formatted = formatCurrency(value);
  return formatted === "N/A" ? formatted : `${formatted}/mo`;
}

export function formatPercent(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }

  const numeric = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(numeric)) {
    return "N/A";
  }

  return `${percentFormatter.format(numeric)}%`;
}

export function formatShortDate(value: string | Date | null | undefined): string {
  if (!value) {
    return "N/A";
  }

  const date =
    value instanceof Date
      ? value
      : /^\d{4}-\d{2}-\d{2}$/.test(value)
        ? new Date(`${value}T12:00:00`)
        : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "N/A";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}
