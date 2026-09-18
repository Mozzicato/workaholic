import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Resume } from "@/features/resumes/api";
import { renderWithQueryClient } from "@/test/render";

import { ResumeList } from "./resume-list";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request: vi.fn() }) }));

const resume: Resume = {
  id: "11111111-1111-4111-8111-111111111111",
  title: "Backend resume",
  target_role: "Junior Backend Engineer",
  document_type: "resume",
  status: "draft",
  current_version_id: null,
  created_at: "2026-09-01T10:00:00Z",
  updated_at: "2026-09-15T10:00:00Z",
};

describe("ResumeList", () => {
  it("links each resume to its own page", () => {
    renderWithQueryClient(<ResumeList resumes={[resume]} />);

    const link = screen.getByRole("link", { name: /Backend resume/ });
    expect(link).toHaveAttribute("href", `/resumes/${resume.id}`);
    expect(link).toHaveTextContent("Junior Backend Engineer");
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("says so plainly when a resume has no target role", () => {
    renderWithQueryClient(<ResumeList resumes={[{ ...resume, target_role: null }]} />);

    expect(screen.getByRole("link", { name: /Backend resume/ })).toHaveTextContent(
      "No target role yet",
    );
  });

  it("offers a way in when there is nothing yet", () => {
    renderWithQueryClient(<ResumeList resumes={[]} />);

    expect(screen.getByText("You haven't created a resume yet.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create" })).toBeInTheDocument();
  });
});
