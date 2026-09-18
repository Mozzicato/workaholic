import { describe, expect, it } from "vitest";

import { isProtectedPath, loginPathFor, safeNextPath } from "./routes";

describe("safeNextPath", () => {
  it.each(["/dashboard", "/resumes/123?tab=ats", "/jobs#top"])(
    "accepts same-site path %s",
    (path) => {
      expect(safeNextPath(path)).toBe(path);
    },
  );

  it.each([
    ["missing", null],
    ["empty", ""],
    ["absolute URL", "https://evil.example/phish"],
    ["protocol-relative URL", "//evil.example"],
    ["backslash trick", "/\\evil.example"],
    ["javascript URL", "javascript:alert(1)"],
    ["control characters", "/dash\nboard"],
  ])("falls back for %s", (_label, candidate) => {
    expect(safeNextPath(candidate)).toBe("/dashboard");
  });
});

describe("isProtectedPath", () => {
  it.each(["/dashboard", "/assistant", "/resumes", "/resumes/abc/editor", "/jobs/1", "/profile"])(
    "protects %s",
    (path) => {
      expect(isProtectedPath(path)).toBe(true);
    },
  );

  it.each(["/", "/login", "/signup", "/learn", "/dashboards-are-public", "/auth/callback"])(
    "leaves %s public",
    (path) => {
      expect(isProtectedPath(path)).toBe(false);
    },
  );
});

describe("loginPathFor", () => {
  it("encodes the return path", () => {
    expect(loginPathFor("/resumes/1?tab=ats")).toBe("/login?next=%2Fresumes%2F1%3Ftab%3Dats");
  });
});
