/** Multi-line text fields hold one list item per line. Blank lines are dropped, not stored. */

export function toLines(values: string[] | undefined): string {
  return (values ?? []).join("\n");
}

export function fromLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

/** Trimmed text, or null: the API treats an absent value as "not stated", never as an empty fact. */
export function orNull(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function toCommas(values: string[] | undefined): string {
  return (values ?? []).join(", ");
}

export function fromCommas(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

/** A year, or a year and month: "2025" or "2025-06". Empty means "not stated". */
export const MONTH_PATTERN = /^\d{4}(-(0[1-9]|1[0-2]))?$/;

export function isMonth(value: string): boolean {
  return MONTH_PATTERN.test(value);
}

/** Compares "2025" and "2025-06" consistently by padding a bare year to its first month. */
export function monthKey(value: string): string {
  return value.includes("-") ? value : `${value}-01`;
}

export function formatMonth(value: string | null | undefined): string | null {
  if (!value) return null;
  if (!value.includes("-")) return value;
  const [year, month] = value.split("-");
  const date = new Date(Number(year), Number(month) - 1, 1);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    year: "numeric",
  }).format(date);
}

/** "Mar 2024 – present", or null when no dates were given. */
export function formatRange(
  start: string | null | undefined,
  end: string | null | undefined,
  isCurrent = false,
): string | null {
  const from = formatMonth(start);
  const to = isCurrent ? "present" : formatMonth(end);
  if (from && to) return `${from} – ${to}`;
  return from ?? to;
}
