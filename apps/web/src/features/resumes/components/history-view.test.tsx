import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { HistoryView } from "./history-view";

const request = vi.fn();
const raw = vi.fn();

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request, raw }) }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const ENTRIES = [
  {
    version_id: "11111111-1111-4111-8111-111111111111",
    resume_id: "aaaaaaaa-1111-4111-8111-111111111111",
    resume_title: "Junior Frontend Engineer — Northwind Payments",
    document_type: "resume",
    target_role: "Junior Frontend Engineer",
    template: "classic",
    version_number: 2,
    label: "Version 2",
    created_at: "2026-09-20T10:00:00Z",
  },
  {
    version_id: "22222222-2222-4222-8222-222222222222",
    resume_id: "bbbbbbbb-2222-4222-8222-222222222222",
    resume_title: "General resume",
    document_type: "resume",
    target_role: null,
    template: "harvard",
    version_number: 1,
    label: "Version 1",
    created_at: "2026-06-01T10:00:00Z",
  },
  {
    version_id: "33333333-3333-4333-8333-333333333333",
    resume_id: "cccccccc-3333-4333-8333-333333333333",
    resume_title: "Andela letter",
    document_type: "cover_letter",
    target_role: "Backend Intern",
    template: "classic",
    version_number: 1,
    label: "Version 1",
    created_at: "2026-03-14T10:00:00Z",
  },
];

describe("HistoryView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.mockResolvedValue(ENTRIES);
  });

  it("keeps everything ever written, newest first", async () => {
    renderWithQueryClient(<HistoryView />);

    expect(
      await screen.findByText("Junior Frontend Engineer — Northwind Payments"),
    ).toBeInTheDocument();
    expect(screen.getByText("General resume")).toBeInTheDocument();
    expect(screen.getByText("Andela letter")).toBeInTheDocument();
  });

  it("finds the one from three months ago by role", async () => {
    const { user } = renderWithQueryClient(<HistoryView />);
    await screen.findByText("General resume");

    await user.type(screen.getByLabelText("Search your history"), "backend");

    expect(screen.getByText("Andela letter")).toBeInTheDocument();
    expect(screen.queryByText("General resume")).not.toBeInTheDocument();
  });

  it("says which are letters and which template each used", async () => {
    renderWithQueryClient(<HistoryView />);

    expect(await screen.findByText(/Cover letter · Backend Intern · Classic/)).toBeInTheDocument();
    expect(screen.getByText(/Resume · Harvard/)).toBeInTheDocument();
  });

  it("says so plainly when nothing has been written", async () => {
    request.mockResolvedValue([]);
    renderWithQueryClient(<HistoryView />);

    expect(await screen.findByText(/Nothing written yet/)).toBeInTheDocument();
  });
});
