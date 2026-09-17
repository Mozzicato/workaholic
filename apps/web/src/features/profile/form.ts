import { z } from "zod";

import { isMonth, monthKey } from "./lines";

/** Dates are deliberately coarse: a resume states months, and a guessed day would be invention. */
export const monthField = z
  .string()
  .trim()
  .refine(
    (value) => value === "" || isMonth(value),
    "Use a year, like 2025, or a year and month, like 2025-06",
  );

export function checkDateOrder(
  values: { start_date: string; end_date: string },
  ctx: z.RefinementCtx,
): void {
  const { start_date: start, end_date: end } = values;
  if (start && end && monthKey(end) < monthKey(start)) {
    ctx.addIssue({
      code: "custom",
      path: ["end_date"],
      message: "The end date comes before the start date",
    });
  }
}
