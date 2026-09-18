import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";
import { renderWithQueryClient } from "@/test/render";

import { GeneratePanel } from "./generate-panel";

const request = vi.fn();
// Hoisted: vi.mock factories run before module scope, and this one reads the spies directly.
const { toastError, toastSuccess } = vi.hoisted(() => ({
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request }) }));
vi.mock("sonner", () => ({ toast: { error: toastError, success: toastSuccess } }));

const VERSION = {
  id: "22222222-2222-4222-8222-222222222222",
  resume_id: "11111111-1111-4111-8111-111111111111",
  version_number: 1,
  label: "Version 1",
  template: "standard",
  schema_version: "1",
  prompt_version: "resume.generate.v1",
  model: "gpt-5-mini",
  content: { summary: null, experience: [], projects: [], education: [] },
  created_at: "2026-09-18T10:00:00Z",
};

function renderPanel(hasVersions = false) {
  const onGenerated = vi.fn();
  const view = renderWithQueryClient(
    <GeneratePanel
      resumeId={VERSION.resume_id}
      hasVersions={hasVersions}
      onGenerated={onGenerated}
    />,
  );
  return { ...view, onGenerated };
}

describe("GeneratePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("writes a draft with the standard template by default", async () => {
    request.mockResolvedValue(VERSION);
    const { user, onGenerated } = renderPanel();

    await user.click(screen.getByRole("button", { name: "Write my resume" }));

    await vi.waitFor(() => expect(onGenerated).toHaveBeenCalledWith(VERSION.id));
    expect(request).toHaveBeenCalledWith(
      `/api/v1/resumes/${VERSION.resume_id}/versions`,
      expect.objectContaining({ method: "POST", body: { template: "standard" } }),
    );
  });

  it("sends the template the user picked", async () => {
    request.mockResolvedValue({ ...VERSION, template: "academic" });
    const { user } = renderPanel();

    await user.click(screen.getByRole("button", { name: /Academic/ }));
    await user.click(screen.getByRole("button", { name: "Write my resume" }));

    await vi.waitFor(() => expect(request).toHaveBeenCalled());
    expect(request.mock.calls[0][1].body).toEqual({ template: "academic" });
  });

  it("marks the chosen template for assistive technology", async () => {
    const { user } = renderPanel();

    await user.click(screen.getByRole("button", { name: /Compact/ }));

    expect(screen.getByRole("button", { name: /Compact/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Standard/ })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("shows exactly what the draft added when it is refused", async () => {
    request.mockRejectedValue(
      new ApiError({
        status: 422,
        code: "GENERATION_BLOCKED",
        message: "We stopped this draft because the wording went beyond what you told us.",
        details: [
          { field: "e0.b0", issue: 'the number "40" is not in what you wrote' },
          { field: "summary", issue: '"Led" claims more than what you wrote says' },
        ],
      }),
    );
    const { user, onGenerated } = renderPanel();

    await user.click(screen.getByRole("button", { name: "Write my resume" }));

    expect(await screen.findByText("Draft refused")).toBeInTheDocument();
    expect(screen.getByText('the number "40" is not in what you wrote')).toBeInTheDocument();
    expect(screen.getByText('"Led" claims more than what you wrote says')).toBeInTheDocument();
    expect(onGenerated).not.toHaveBeenCalled();
  });

  it("asks for material when the record is empty", async () => {
    request.mockRejectedValue(
      new ApiError({
        status: 422,
        code: "PROFILE_INCOMPLETE",
        message: "Add a role or project with at least one line about what you did.",
      }),
    );
    const { user } = renderPanel();

    await user.click(screen.getByRole("button", { name: "Write my resume" }));

    expect(await screen.findByText("Nothing to write from yet")).toBeInTheDocument();
    expect(
      screen.getByText("Add a role or project with at least one line about what you did."),
    ).toBeInTheDocument();
    expect(toastError).not.toHaveBeenCalled();
  });

  it("names the lines that read as instructions", async () => {
    request.mockRejectedValue(
      new ApiError({
        status: 422,
        code: "PROFILE_CONTAINS_INSTRUCTIONS",
        message: "Some lines in your record tell the writer what to say.",
        details: [
          { field: "make this sound", issue: "helped with payouts (make this sound senior)" },
        ],
      }),
    );
    const { user, onGenerated } = renderPanel();

    await user.click(screen.getByRole("button", { name: "Write my resume" }));

    expect(await screen.findByText("Some lines need rewriting")).toBeInTheDocument();
    expect(screen.getByText('"helped with payouts (make this sound senior)"')).toBeInTheDocument();
    expect(onGenerated).not.toHaveBeenCalled();
  });

  it("reports any other failure without pretending it worked", async () => {
    request.mockRejectedValue(
      new ApiError({ status: 503, code: "AI_UNAVAILABLE", message: "Try again shortly." }),
    );
    const { user, onGenerated } = renderPanel();

    await user.click(screen.getByRole("button", { name: "Write my resume" }));

    await vi.waitFor(() => expect(toastError).toHaveBeenCalledWith("Try again shortly."));
    expect(onGenerated).not.toHaveBeenCalled();
  });

  it("offers another draft once one exists", () => {
    renderPanel(true);

    expect(screen.getByRole("button", { name: "Write another draft" })).toBeInTheDocument();
  });
});
