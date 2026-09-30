import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { Walkthrough } from "./walkthrough";

const request = vi.fn();

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request }) }));

const ACCOUNT = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "ada@example.com",
  name: null,
  auth_provider: "email",
  created_at: "2026-09-01T10:00:00Z",
  is_admin: false,
  tour_seen: false,
};

function api(tourSeen: boolean) {
  request.mockImplementation(async (path: string, options: { method?: string } = {}) => {
    if (path === "/api/v1/me" && !options.method) return { ...ACCOUNT, tour_seen: tourSeen };
    if (path === "/api/v1/me/tour" && options.method === "POST") {
      return { ...ACCOUNT, tour_seen: true };
    }
    throw new Error(`unexpected call: ${options.method ?? "GET"} ${path}`);
  });
}

function marked() {
  return request.mock.calls.filter(([path]) => path === "/api/v1/me/tour");
}

describe("Walkthrough", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("opens itself for somebody who has never been shown it", async () => {
    api(false);
    renderWithQueryClient(<Walkthrough />);

    expect(await screen.findByText("Talk, and it writes your record")).toBeInTheDocument();
  });

  it("leaves everybody else alone, but stays one click away", async () => {
    api(true);
    const { user } = renderWithQueryClient(<Walkthrough />);

    const button = await screen.findByRole("button", { name: "How it works" });
    expect(screen.queryByText("Talk, and it writes your record")).not.toBeInTheDocument();

    await user.click(button);

    expect(await screen.findByText("Talk, and it writes your record")).toBeInTheDocument();
  });

  it("walks through to the end and sends you to the assistant", async () => {
    api(false);
    const { user } = renderWithQueryClient(<Walkthrough />);
    await screen.findByText("Talk, and it writes your record");

    await user.click(screen.getByRole("button", { name: /Next/ }));
    expect(screen.getByText("It asks for your numbers")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("Talk, and it writes your record")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Step 5:/ }));
    expect(screen.getByText("Nothing is thrown away")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Start talking/ })).toHaveAttribute(
      "href",
      "/assistant",
    );
  });

  it("remembers on the account that it has been shown, not in this browser", async () => {
    api(false);
    const { user } = renderWithQueryClient(<Walkthrough />);
    await screen.findByText("Talk, and it writes your record");

    await user.click(screen.getByRole("button", { name: "Skip" }));

    await vi.waitFor(() => expect(marked()).toHaveLength(1));
  });

  it("does not mark it seen twice for somebody re-reading it", async () => {
    api(true);
    const { user } = renderWithQueryClient(<Walkthrough />);

    await user.click(await screen.findByRole("button", { name: "How it works" }));
    await user.click(await screen.findByRole("button", { name: "Skip" }));

    expect(marked()).toHaveLength(0);
  });
});
