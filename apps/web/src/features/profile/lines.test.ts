import { describe, expect, it } from "vitest";

import {
  formatMonth,
  formatRange,
  fromCommas,
  fromLines,
  isMonth,
  monthKey,
  orNull,
  toCommas,
  toLines,
} from "./lines";

describe("fromLines", () => {
  it("keeps one item per line and drops the empty ones", () => {
    expect(fromLines("Built the payouts service\n\n  Mentored two interns  \n")).toEqual([
      "Built the payouts service",
      "Mentored two interns",
    ]);
  });

  it("returns nothing for blank text rather than an empty claim", () => {
    expect(fromLines("   \n\n ")).toEqual([]);
  });

  it("round-trips through toLines", () => {
    const items = ["One", "Two"];
    expect(fromLines(toLines(items))).toEqual(items);
  });
});

describe("fromCommas", () => {
  it("splits and trims", () => {
    expect(fromCommas("Python, PostgreSQL ,Docker")).toEqual(["Python", "PostgreSQL", "Docker"]);
  });

  it("ignores stray separators", () => {
    expect(fromCommas(" , ,")).toEqual([]);
    expect(fromCommas(toCommas(["a", "b"]))).toEqual(["a", "b"]);
  });
});

describe("orNull", () => {
  it("turns blank input into null instead of an empty string", () => {
    expect(orNull("   ")).toBeNull();
    expect(orNull(undefined)).toBeNull();
    expect(orNull("  Lagos ")).toBe("Lagos");
  });
});

describe("isMonth", () => {
  it("accepts a year, or a year and month", () => {
    expect(isMonth("2025")).toBe(true);
    expect(isMonth("2025-01")).toBe(true);
    expect(isMonth("2025-12")).toBe(true);
  });

  it("rejects anything else", () => {
    for (const value of ["2025-13", "2025-00", "25-01", "2025-1", "March 2025", ""]) {
      expect(isMonth(value)).toBe(false);
    }
  });
});

describe("monthKey", () => {
  it("compares a bare year against a month consistently", () => {
    expect(monthKey("2025") < monthKey("2025-06")).toBe(true);
    expect(monthKey("2025-06") < monthKey("2026")).toBe(true);
  });
});

describe("formatMonth", () => {
  it("leaves a bare year alone", () => {
    expect(formatMonth("2025")).toBe("2025");
  });

  it("names the month without shifting it across a time zone", () => {
    expect(formatMonth("2025-01")).toContain("2025");
    expect(formatMonth("2025-01")).toMatch(/jan/i);
  });

  it("has nothing to show for a missing date", () => {
    expect(formatMonth(null)).toBeNull();
    expect(formatMonth(undefined)).toBeNull();
  });
});

describe("formatRange", () => {
  it("says present for a current role", () => {
    expect(formatRange("2024-03", null, true)).toMatch(/– present$/);
  });

  it("falls back to whichever date exists", () => {
    expect(formatRange("2024", null)).toBe("2024");
    expect(formatRange(null, "2025")).toBe("2025");
    expect(formatRange(null, null)).toBeNull();
  });
});
