import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TEMPLATES } from "@/features/resumes/templates";
import { renderWithQueryClient } from "@/test/render";

import { TemplateGallery } from "./template-gallery";

vi.mock("@/lib/api/browser", () => ({
  getApiClient: () => ({ request: vi.fn(), upload: vi.fn() }),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

describe("TemplateGallery", () => {
  it("shows one template large, readable, with the rest as a strip", () => {
    renderWithQueryClient(<TemplateGallery value="classic" onChange={vi.fn()} />);

    // The big one is described for a screen reader; the strip is decoration you click.
    expect(
      screen.getByAltText(/The Classic template, filled in with an example person/),
    ).toBeInTheDocument();
    expect(screen.getByText(`(1 of ${TEMPLATES.length})`)).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(TEMPLATES.length);
  });

  it("moves to the next and previous template", async () => {
    const onChange = vi.fn();
    const { user } = renderWithQueryClient(<TemplateGallery value="classic" onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: "Next template" }));
    expect(onChange).toHaveBeenLastCalledWith(TEMPLATES[1].key);

    await user.click(screen.getByRole("button", { name: "Previous template" }));
    // Wraps to the end rather than stopping.
    expect(onChange).toHaveBeenLastCalledWith(TEMPLATES[TEMPLATES.length - 1].key);
  });

  it("describes what the one on screen is for", () => {
    renderWithQueryClient(<TemplateGallery value="sidebar" onChange={vi.fn()} />);

    expect(screen.getByText(/Work on the left/)).toBeInTheDocument();
    expect(screen.getByText(/some older applicant-tracking systems/)).toBeInTheDocument();
  });

  it("offers to take a template someone already has", () => {
    renderWithQueryClient(<TemplateGallery value="classic" onChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: /Have your own template/ })).toBeInTheDocument();
  });
});
