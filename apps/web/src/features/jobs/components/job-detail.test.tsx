import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { JobDetail } from "./job-detail";

const request = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request }) }));
vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const JOB_ID = "33333333-3333-4333-8333-333333333333";
const ADVERT = "Junior Backend Engineer. Required: Python, AWS.";

const EMPTY_ANALYSIS = {
  role: "",
  seniority: "",
  required_skills: [],
  preferred_skills: [],
  responsibilities: [],
  qualifications: [],
  keywords: [],
  domain_terms: [],
  education_requirements: [],
  experience_requirements: [],
};

function job(analysis: Record<string, unknown> = {}) {
  return {
    id: JOB_ID,
    title: "Junior Backend Engineer",
    company: "Northwind",
    source_url: null,
    raw_text: ADVERT,
    analysis: { ...EMPTY_ANALYSIS, ...analysis },
    analysis_model: "gpt-5-mini",
    prompt_version: "job.analyse.v1",
    created_at: "2026-09-18T10:00:00Z",
    updated_at: "2026-09-18T10:00:00Z",
  };
}

const REPORT = {
  job_id: JOB_ID,
  matched: 1,
  partially_matched: 1,
  not_found: 1,
  matches: [
    {
      requirement: "Python",
      state: "MATCHED",
      kind: "required",
      evidence: ["Python"],
      explanation: "You list this as a skill.",
    },
    {
      requirement: "Docker",
      state: "PARTIALLY_MATCHED",
      kind: "required",
      evidence: ["we deployed with Docker"],
      explanation: "Mentioned, not listed.",
    },
    {
      requirement: "AWS",
      state: "NOT_FOUND",
      kind: "preferred",
      evidence: [],
      explanation: "Your record doesn't mention this.",
    },
  ],
};

function api(jobBody: unknown) {
  request.mockImplementation(async (path: string) => {
    if (path === `/api/v1/jobs/${JOB_ID}`) return jobBody;
    if (path === `/api/v1/jobs/${JOB_ID}/match`) return REPORT;
    throw new Error(`unexpected call: ${path}`);
  });
}

describe("JobDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows what the record supports, partly supports and does not mention", async () => {
    api(job({ required_skills: ["Python", "Docker"], preferred_skills: ["AWS"] }));
    renderWithQueryClient(<JobDetail id={JOB_ID} />);

    expect(await screen.findByText("Python")).toBeInTheDocument();
    expect(screen.getByText(/In your record/)).toBeInTheDocument();
    expect(screen.getByText(/Mentioned, not listed/)).toBeInTheDocument();
    expect(screen.getByText(/Not in your record/)).toBeInTheDocument();
  });

  it("says plainly that nothing is added for the user", async () => {
    api(job({ required_skills: ["Python"] }));
    renderWithQueryClient(<JobDetail id={JOB_ID} />);

    expect(await screen.findByText(/nothing is added to it/)).toBeInTheDocument();
  });

  it("quotes where in the record a requirement was found", async () => {
    api(job({ required_skills: ["Docker"] }));
    renderWithQueryClient(<JobDetail id={JOB_ID} />);

    expect(await screen.findByText(/we deployed with Docker/)).toBeInTheDocument();
  });

  it("keeps the advert exactly as it was pasted", async () => {
    api(job({ required_skills: ["Python"] }));
    renderWithQueryClient(<JobDetail id={JOB_ID} />);

    expect(await screen.findByText(ADVERT)).toBeInTheDocument();
  });

  it("offers to read an advert that was saved without being analysed", async () => {
    api(job());
    renderWithQueryClient(<JobDetail id={JOB_ID} />);

    expect(await screen.findByRole("button", { name: "Read it now" })).toBeInTheDocument();
    expect(request).not.toHaveBeenCalledWith(`/api/v1/jobs/${JOB_ID}/match`, expect.anything());
  });
});
