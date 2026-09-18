import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Education } from "@/features/profile/api";
import { renderWithQueryClient } from "@/test/render";

import { EducationSection } from "./education-section";

const request = vi.fn();

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request }) }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const school: Education = {
  id: "edu-1",
  institution: "University of Lagos",
  qualification: "BSc",
  field_of_study: "Computer Science",
  grade: "4.52/5",
  start_date: "2022",
  end_date: "2026",
};

function renderSection(education: Education[] = []) {
  return renderWithQueryClient(<EducationSection education={education} />);
}

describe("EducationSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.mockResolvedValue({ education: [] });
  });

  it("shows the school, the course and the grade", () => {
    renderSection([school]);

    expect(screen.getByText("University of Lagos")).toBeInTheDocument();
    expect(screen.getByText("BSc, Computer Science")).toBeInTheDocument();
    expect(screen.getByText(/Grade: 4\.52\/5/)).toBeInTheDocument();
  });

  it("needs the school, and nothing else", async () => {
    const { user } = renderSection();

    await user.click(screen.getByRole("button", { name: "Add your school" }));
    await user.click(screen.getByRole("button", { name: "Add education" }));

    expect(await screen.findByText("Where did you study?")).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });

  it("saves the grade exactly as typed", async () => {
    const { user } = renderSection();

    await user.click(screen.getByRole("button", { name: "Add your school" }));
    await user.type(screen.getByLabelText("School"), "University of Lagos");
    await user.type(screen.getByLabelText("Grade or CGPA (optional)"), "Second Class Upper");
    await user.click(screen.getByRole("button", { name: "Add education" }));

    await vi.waitFor(() => expect(request).toHaveBeenCalled());
    const [path, options] = request.mock.calls[0];
    expect(path).toBe("/api/v1/profile");
    expect(options.body.education).toEqual([
      {
        institution: "University of Lagos",
        qualification: null,
        field_of_study: null,
        grade: "Second Class Upper",
        start_date: null,
        end_date: null,
      },
    ]);
  });

  it("keeps the id when an entry is edited, so its evidence still points at it", async () => {
    const { user } = renderSection([school]);

    await user.click(screen.getByRole("button", { name: "Edit University of Lagos" }));
    await user.clear(screen.getByLabelText("Grade or CGPA (optional)"));
    await user.type(screen.getByLabelText("Grade or CGPA (optional)"), "4.6/5");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await vi.waitFor(() => expect(request).toHaveBeenCalled());
    expect(request.mock.calls[0][1].body.education[0]).toMatchObject({
      id: "edu-1",
      grade: "4.6/5",
    });
  });
});
