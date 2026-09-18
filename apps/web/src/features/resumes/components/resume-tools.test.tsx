import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { ResumeTools } from "./resume-tools";

const request = vi.fn();
vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request }) }));
vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const RESUME_ID = "11111111-1111-4111-8111-111111111111";
const VERSION_ID = "22222222-2222-4222-8222-222222222222";
const JOB_ID = "33333333-3333-4333-8333-333333333333";

const REPORT = {
  score: 86,
  maximum: 100,
  categories: [
    {
      category: "Structure",
      score: 20,
      maximum: 20,
      explanation: "Everything checked here passed.",
    },
    {
      category: "Text extraction",
      score: 20,
      maximum: 20,
      explanation: "Everything checked here passed.",
    },
    {
      category: "Keyword alignment",
      score: 10,
      maximum: 20,
      explanation: "Lost points on: Keyword coverage.",
    },
    {
      category: "Formatting",
      score: 20,
      maximum: 20,
      explanation: "Everything checked here passed.",
    },
    {
      category: "Content quality",
      score: 16,
      maximum: 20,
      explanation: "Lost points on: Some measurable detail.",
    },
  ],
  checks: [
    {
      category: "Content quality",
      name: "Some measurable detail",
      passed: false,
      detail: "No line includes a number.",
    },
  ],
  caveat:
    "This is the Workaholic ATS Compatibility Score, not a universal one. Employers run different systems.",
};

function api() {
  request.mockImplementation(async (path: string) => {
    if (path === "/api/v1/jobs") {
      return [
        {
          id: JOB_ID,
          title: "Junior Backend",
          company: "Northwind",
          created_at: "2026-09-18T10:00:00Z",
          updated_at: "2026-09-18T10:00:00Z",
        },
      ];
    }
    if (path.includes("/ats")) return REPORT;
    if (path.endsWith("/tailored")) {
      return {
        version: {
          id: "44444444-4444-4444-8444-444444444444",
          resume_id: RESUME_ID,
          version_number: 2,
          label: "Version 2",
          template: "standard",
          created_at: "2026-09-18T11:00:00Z",
          schema_version: "1",
          prompt_version: "resume.generate.v2",
          model: "gpt-5-mini",
          content: { summary: null, experience: [], projects: [], education: [] },
        },
        summary: {
          changed: ["Reordered your roles so the most relevant comes first"],
          unchanged: ["Employers, job titles and dates", "The wording of every bullet"],
          missing_requirements: ["AWS"],
        },
      };
    }
    throw new Error(`unexpected call: ${path}`);
  });
}

function renderTools() {
  const onTailored = vi.fn();
  const view = renderWithQueryClient(
    <ResumeTools resumeId={RESUME_ID} versionId={VERSION_ID} onTailored={onTailored} />,
  );
  return { ...view, onTailored };
}

describe("ResumeTools", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api();
  });

  it("shows the score with its name, its parts and its caveat", async () => {
    const { user } = renderTools();

    await user.click(await screen.findByRole("button", { name: "Check ATS compatibility" }));

    expect(await screen.findByText("Workaholic ATS Compatibility Score")).toBeInTheDocument();
    expect(screen.getByText("86")).toBeInTheDocument();
    expect(screen.getByText("Keyword alignment")).toBeInTheDocument();
    expect(screen.getByText(/not a universal one/)).toBeInTheDocument();
  });

  it("lists what lost points and why", async () => {
    const { user } = renderTools();

    await user.click(await screen.findByRole("button", { name: "Check ATS compatibility" }));

    expect(await screen.findByText(/No line includes a number/)).toBeInTheDocument();
  });

  it("does not print a PDF until asked", async () => {
    renderTools();

    await screen.findByRole("button", { name: "Check ATS compatibility" });
    expect(request).not.toHaveBeenCalledWith(expect.stringContaining("/ats"), expect.anything());
  });

  it("tailors to a chosen job and reports what moved and what is missing", async () => {
    const { user, onTailored } = renderTools();

    await user.selectOptions(await screen.findByLabelText("Job"), JOB_ID);
    await user.click(screen.getByRole("button", { name: "Tailor a copy to this job" }));

    expect(await screen.findByText(/Reordered your roles/)).toBeInTheDocument();
    expect(screen.getByText(/The wording of every bullet/)).toBeInTheDocument();
    expect(screen.getByText(/AWS\. These were not added/)).toBeInTheDocument();
    expect(onTailored).toHaveBeenCalledWith("44444444-4444-4444-8444-444444444444");
  });

  it("sends the chosen job with the ATS check", async () => {
    const { user } = renderTools();

    await user.selectOptions(await screen.findByLabelText("Job"), JOB_ID);
    await user.click(screen.getByRole("button", { name: "Check ATS compatibility" }));

    await vi.waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        `/api/v1/resumes/${RESUME_ID}/versions/${VERSION_ID}/ats?job_id=${JOB_ID}`,
        expect.anything(),
      ),
    );
  });
});
