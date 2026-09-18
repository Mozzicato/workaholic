import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { ImportSection } from "./import-section";

const request = vi.fn();
const upload = vi.fn();
vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request, upload }) }));
vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const PROPOSAL = {
  kind: "docx",
  pages: 0,
  prompt_version: "documents.parse.v1",
  model: "gpt-5-mini",
  dropped: ["Kubernetes"],
  contents: {
    full_name: "Ada Lovelace",
    email: "ada@example.com",
    phone: "",
    location: "Lagos, Nigeria",
    headline: "",
    summary: "",
    roles: [
      {
        employer: "Lumen Freight",
        title: "Backend Engineer Intern",
        start_date: "2025-06",
        end_date: "2025-09",
        bullets: ["Wrote tests for the pricing module"],
        technologies: ["Python"],
      },
    ],
    projects: [],
    education: [
      {
        institution: "University of Lagos",
        qualification: "BSc Computer Science",
        field_of_study: "",
        start_date: "2022",
        end_date: "2026",
      },
    ],
    skills: ["Python", "PostgreSQL"],
  },
};

async function uploaded() {
  upload.mockResolvedValue(PROPOSAL);
  const view = renderWithQueryClient(<ImportSection />);
  const file = new File(["fake"], "cv.docx", {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
  await view.user.upload(screen.getByLabelText("Choose a resume to upload"), file);
  await screen.findByText("Backend Engineer Intern at Lumen Freight");
  return view.user;
}

describe("ImportSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.mockResolvedValue({ added: [], skipped: [] });
  });

  it("proposes what the document says, everything ticked", async () => {
    await uploaded();

    expect(screen.getByText("BSc Computer Science, University of Lagos")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add 4 to my record" })).toBeInTheDocument();
  });

  it("records nothing just by uploading", async () => {
    await uploaded();

    expect(request).not.toHaveBeenCalled();
  });

  it("shows what the document did not support", async () => {
    await uploaded();

    expect(screen.getByText(/didn't say it: Kubernetes/)).toBeInTheDocument();
  });

  it("adds only what stays ticked", async () => {
    const user = await uploaded();

    await user.click(screen.getByRole("checkbox", { name: /PostgreSQL/ }));
    await user.click(screen.getByRole("button", { name: "Add 3 to my record" }));

    await vi.waitFor(() => expect(request).toHaveBeenCalled());
    const body = request.mock.calls[0][1].body;
    expect(body.skills).toEqual(["Python"]);
    expect(body.roles).toHaveLength(1);
    expect(request.mock.calls[0][0]).toBe("/api/v1/documents/import/accept");
  });

  it("can be discarded without recording anything", async () => {
    const user = await uploaded();

    await user.click(screen.getByRole("button", { name: "Discard" }));

    expect(screen.getByRole("button", { name: "Upload a resume" })).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });
});
