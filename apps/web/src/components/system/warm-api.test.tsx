import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WarmApi } from "./warm-api";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("WarmApi", () => {
  it("starts the API while the person is still on the page", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}"));

    render(<WarmApi />);

    expect(fetchSpy).toHaveBeenCalledWith("http://api.test/health", { cache: "no-store" });
  });

  it("renders nothing", () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}"));

    const { container } = render(<WarmApi />);

    expect(container).toBeEmptyDOMElement();
  });

  it("is a nudge, not a dependency: a failure is swallowed", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));

    expect(() => render(<WarmApi />)).not.toThrow();
    // An unhandled rejection here would fail the run; reaching this line is the assertion.
    await Promise.resolve();
  });
});
