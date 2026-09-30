import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { RecordAdvice } from "./record-advice";

const request = vi.fn();
const push = vi.fn();
const { toastSuccess } = vi.hoisted(() => ({ toastSuccess: vi.fn() }));

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request }) }));
vi.mock("sonner", () => ({ toast: { success: toastSuccess, error: vi.fn() } }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const PROFILE = {
  id: "44444444-4444-4444-8444-444444444444",
  basics: {},
  links: { other: [] },
  experience: [],
  education: [
    { id: "s1", institution: "Unilag", qualification: "BSc", grade: "2.8/5" },
    { id: "s2", institution: "Yabatech", qualification: "ND", grade: "3.9/4" },
  ],
  projects: [],
  skills: [],
  achievements: [],
  certifications: [],
  languages: [],
  updated_at: "2026-09-30T10:00:00Z",
};

const ADVICE = {
  critical: 1,
  important: 1,
  items: [
    {
      key: "nothing-done",
      severity: 1,
      action: "build",
      title: "There is nothing here to hire you for",
      detail: "A resume with no job and no project gives a recruiter nothing to read.",
      todo: "Build one thing and write it down here.",
      item_id: null,
    },
    {
      key: "unmeasured-experience-0",
      severity: 2,
      action: "answer",
      title: "Nothing about Intern at Andela has a number in it",
      detail: "Numbers are what make a line land.",
      todo: "Answer a couple of questions and we will put it in.",
      item_id: "r1",
    },
    {
      key: "low-grade-0",
      severity: 2,
      action: "remove",
      title: "Your grade (2.8/5) is working against you",
      detail: "Most graduate screens filter around a 2:1 or 3.5 out of 5.",
      todo: "Leave it off.",
      item_id: "s1",
    },
  ],
};

function api(advice: unknown = ADVICE) {
  request.mockImplementation(async (path: string, options: { method?: string } = {}) => {
    if (String(path).startsWith("/api/v1/profile/advice")) return advice;
    if (path === "/api/v1/profile" && options.method === "PATCH") return PROFILE;
    if (path === "/api/v1/profile") return PROFILE;
    throw new Error(`unexpected call: ${path}`);
  });
}

describe("RecordAdvice", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("says the hard thing first", async () => {
    api();
    renderWithQueryClient(<RecordAdvice />);

    expect(await screen.findByText("There is nothing here to hire you for")).toBeInTheDocument();
    expect(screen.getByText(/A resume written from this would struggle/)).toBeInTheDocument();
  });

  it("sends them to the assistant for things it can simply ask about", async () => {
    api();
    const { user } = renderWithQueryClient(<RecordAdvice />);

    await user.click((await screen.findAllByRole("button", { name: "Answer" }))[0]);

    expect(push).toHaveBeenCalledWith("/assistant");
  });

  it("leaves a low grade off the record when they agree, and only that grade", async () => {
    api();
    const { user } = renderWithQueryClient(<RecordAdvice />);

    await user.click(await screen.findByRole("button", { name: /Leave it off/ }));

    await vi.waitFor(() => expect(toastSuccess).toHaveBeenCalled());
    const patched = request.mock.calls.find(([, options]) => options?.method === "PATCH");
    expect(patched?.[1].body.education).toEqual([
      { id: "s1", institution: "Unilag", qualification: "BSc", grade: null },
      { id: "s2", institution: "Yabatech", qualification: "ND", grade: "3.9/4" },
    ]);
  });

  it("says so plainly when there is nothing to fix", async () => {
    api({ items: [], critical: 0, important: 0 });
    renderWithQueryClient(<RecordAdvice />);

    expect(await screen.findByText(/Nothing here is holding your resume back/)).toBeInTheDocument();
  });
});
