import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";
import { renderWithQueryClient } from "@/test/render";

import { CreateResumeDialog } from "./create-resume-dialog";

const request = vi.fn();
const router = { push: vi.fn() };

vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request }) }));

const resume = {
  id: "11111111-1111-4111-8111-111111111111",
  title: "Backend resume",
  target_role: "Junior Backend Engineer",
  document_type: "resume",
  template: "classic",
  status: "draft",
  current_version_id: null,
  created_at: "2026-09-17T10:00:00Z",
  updated_at: "2026-09-17T10:00:00Z",
};

async function openDialog() {
  const view = renderWithQueryClient(<CreateResumeDialog />);
  await view.user.click(screen.getByRole("button", { name: "Create" }));
  return view.user;
}

/** Past the template step, keeping whatever look is selected. */
async function toDetails() {
  const user = await openDialog();
  await user.click(screen.getByRole("button", { name: /^Continue with/ }));
  return user;
}

describe("CreateResumeDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates a cover letter when that is what was chosen", async () => {
    request.mockResolvedValue({ ...resume, document_type: "cover_letter" });
    const user = await openDialog();

    await user.click(screen.getByRole("button", { name: /Cover letter/ }));
    await user.type(screen.getByLabelText("Name"), "Northwind letter");
    await user.click(screen.getByRole("button", { name: "Create letter" }));

    await vi.waitFor(() => expect(request).toHaveBeenCalled());
    expect(request.mock.calls[0][1].body.document_type).toBe("cover_letter");
  });

  it("opens on the templates, with Classic chosen", async () => {
    await openDialog();

    expect(screen.getByRole("heading", { name: "Choose a template" })).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(11);
    expect(screen.getByRole("radio", { name: /Classic/ })).toHaveAttribute("aria-checked", "true");
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
  });

  it("creates the resume in the template that was picked", async () => {
    request.mockResolvedValue({ ...resume, template: "harvard" });
    const user = await openDialog();

    await user.click(screen.getByRole("radio", { name: /Harvard/ }));
    await user.click(screen.getByRole("button", { name: "Continue with Harvard" }));
    expect(screen.getByText("Harvard")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Name"), "Backend resume");
    await user.click(screen.getByRole("button", { name: "Create resume" }));

    await vi.waitFor(() => expect(request).toHaveBeenCalled());
    expect(request.mock.calls[0][1].body.template).toBe("harvard");
  });

  it("warns that two columns can trip an older ATS", async () => {
    const user = await openDialog();

    await user.click(screen.getByRole("radio", { name: /Sidebar/ }));

    expect(screen.getByText(/some older applicant-tracking systems/)).toBeInTheDocument();
  });

  it("can go back and change the template before creating", async () => {
    const user = await toDetails();

    await user.click(screen.getByRole("button", { name: "Change" }));

    expect(screen.getByRole("heading", { name: "Choose a template" })).toBeInTheDocument();
  });

  it("requires a name before calling the API", async () => {
    const user = await toDetails();

    await user.click(screen.getByRole("button", { name: "Create resume" }));

    expect(await screen.findByText("Give this document a name")).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });

  it("creates the resume and opens it", async () => {
    request.mockResolvedValue(resume);
    const user = await toDetails();

    await user.type(screen.getByLabelText("Name"), "  Backend resume ");
    await user.type(screen.getByLabelText("Target role (optional)"), "Junior Backend Engineer");
    await user.click(screen.getByRole("button", { name: "Create resume" }));

    await vi.waitFor(() => expect(router.push).toHaveBeenCalledWith(`/resumes/${resume.id}`));
    expect(request).toHaveBeenCalledWith(
      "/api/v1/resumes",
      expect.objectContaining({
        method: "POST",
        body: {
          title: "Backend resume",
          target_role: "Junior Backend Engineer",
          document_type: "resume",
          template: "classic",
        },
      }),
    );
  });

  it("sends no target role rather than an empty one", async () => {
    request.mockResolvedValue({ ...resume, target_role: null });
    const user = await toDetails();

    await user.type(screen.getByLabelText("Name"), "Backend resume");
    await user.click(screen.getByRole("button", { name: "Create resume" }));

    await vi.waitFor(() => expect(request).toHaveBeenCalled());
    expect(request.mock.calls[0][1].body).toEqual({
      title: "Backend resume",
      target_role: null,
      document_type: "resume",
      template: "classic",
    });
  });

  it("explains a duplicate name in the user's terms", async () => {
    request.mockRejectedValue(
      new ApiError({ status: 409, code: "conflict", message: "Resume title already used" }),
    );
    const user = await toDetails();

    await user.type(screen.getByLabelText("Name"), "Backend resume");
    await user.click(screen.getByRole("button", { name: "Create resume" }));

    expect(
      await screen.findByText("You already have a document with that name."),
    ).toBeInTheDocument();
    expect(router.push).not.toHaveBeenCalled();
  });
});
