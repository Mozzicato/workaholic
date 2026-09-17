import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Experience } from "@/features/profile/api";
import { renderWithQueryClient } from "@/test/render";

import { ExperienceSection } from "./experience-section";

const request = vi.fn();

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request }) }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const role: Experience = {
  id: "role-1",
  employer: "Paystack",
  title: "Backend Engineer",
  location: "Lagos, Nigeria",
  is_current: false,
  start_date: "2024-03",
  end_date: "2025-06",
  bullets: ["Built the payouts reconciliation service"],
  technologies: ["Python", "PostgreSQL"],
};

function renderSection(experience: Experience[] = []) {
  return renderWithQueryClient(<ExperienceSection experience={experience} />);
}

describe("ExperienceSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.mockResolvedValue({ experience: [] });
  });

  it("shows what the user recorded, and nothing more", () => {
    renderSection([role]);

    expect(screen.getByText("Backend Engineer · Paystack")).toBeInTheDocument();
    expect(screen.getByText("Built the payouts reconciliation service")).toBeInTheDocument();
    expect(screen.getByText("Python, PostgreSQL")).toBeInTheDocument();
  });

  it("asks for the role and employer before saving anything", async () => {
    const { user } = renderSection();

    await user.click(screen.getByRole("button", { name: "Add your first role" }));
    await user.click(screen.getByRole("button", { name: "Add role" }));

    expect(await screen.findByText("What was your role?")).toBeInTheDocument();
    expect(screen.getByText("Who was this for?")).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });

  it("rejects a date it cannot trust", async () => {
    const { user } = renderSection();

    await user.click(screen.getByRole("button", { name: "Add your first role" }));
    await user.type(screen.getByLabelText("Role"), "Backend Engineer");
    await user.type(screen.getByLabelText("Employer"), "Paystack");
    await user.type(screen.getByLabelText("Started"), "March 2024");
    await user.click(screen.getByRole("button", { name: "Add role" }));

    expect(
      await screen.findByText("Use a year, like 2025, or a year and month, like 2025-06"),
    ).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });

  it("rejects an end date that comes before the start", async () => {
    const { user } = renderSection();

    await user.click(screen.getByRole("button", { name: "Add your first role" }));
    await user.type(screen.getByLabelText("Role"), "Backend Engineer");
    await user.type(screen.getByLabelText("Employer"), "Paystack");
    await user.type(screen.getByLabelText("Started"), "2025-06");
    await user.type(screen.getByLabelText("Ended"), "2024-03");
    await user.click(screen.getByRole("button", { name: "Add role" }));

    expect(
      await screen.findByText("The end date comes before the start date"),
    ).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });

  it("saves the whole list with the new role appended", async () => {
    const { user } = renderSection([role]);

    await user.click(screen.getByRole("button", { name: "Add role" }));
    await user.type(screen.getByLabelText("Role"), "Intern");
    await user.type(screen.getByLabelText("Employer"), "Unilag");
    await user.type(screen.getByLabelText("Started"), "2023-06");
    await user.click(screen.getByRole("checkbox", { name: "I still work here" }));
    await user.type(
      screen.getByLabelText("What you did"),
      "Wrote the lab scheduling script\n\nTrained the new interns",
    );
    await user.type(screen.getByLabelText("Tools used (optional)"), "Python, Bash");
    await user.click(screen.getByRole("button", { name: "Add role" }));

    await vi.waitFor(() => expect(request).toHaveBeenCalled());
    const body = request.mock.calls[0][1].body;
    expect(body.experience).toHaveLength(2);
    expect(body.experience[1]).toEqual({
      employer: "Unilag",
      title: "Intern",
      location: null,
      is_current: true,
      start_date: "2023-06",
      end_date: null,
      bullets: ["Wrote the lab scheduling script", "Trained the new interns"],
      technologies: ["Python", "Bash"],
    });
  });

  it("keeps the identifiers of an edited role instead of replacing it", async () => {
    const { user } = renderSection([role]);

    await user.click(screen.getByRole("button", { name: "Edit Backend Engineer at Paystack" }));
    await user.clear(screen.getByLabelText("Role"));
    await user.type(screen.getByLabelText("Role"), "Senior Backend Engineer");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await vi.waitFor(() => expect(request).toHaveBeenCalled());
    const body = request.mock.calls[0][1].body;
    expect(body.experience).toHaveLength(1);
    expect(body.experience[0]).toMatchObject({
      id: "role-1",
      title: "Senior Backend Engineer",
      employer: "Paystack",
      bullets: ["Built the payouts reconciliation service"],
    });
  });

  it("removes only the role asked for", async () => {
    const second: Experience = { ...role, id: "role-2", employer: "Flutterwave" };
    const { user } = renderSection([role, second]);

    await user.click(screen.getByRole("button", { name: "Remove Backend Engineer at Paystack" }));

    await vi.waitFor(() => expect(request).toHaveBeenCalled());
    expect(request.mock.calls[0][1].body.experience).toEqual([second]);
  });
});
