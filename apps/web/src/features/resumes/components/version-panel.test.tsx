import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { VersionPanel } from "./version-panel";

const request = vi.fn();
const raw = vi.fn();
const { toastError } = vi.hoisted(() => ({ toastError: vi.fn() }));

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request, raw }) }));
vi.mock("sonner", () => ({ toast: { error: toastError, success: vi.fn() } }));

const RESUME_ID = "11111111-1111-4111-8111-111111111111";

const VERSIONS = [
  {
    id: "22222222-2222-4222-8222-222222222222",
    resume_id: RESUME_ID,
    version_number: 2,
    label: "Version 2",
    template: "compact",
    created_at: "2026-09-18T12:00:00Z",
  },
  {
    id: "33333333-3333-4333-8333-333333333333",
    resume_id: RESUME_ID,
    version_number: 1,
    label: "Version 1",
    template: "standard",
    created_at: "2026-09-18T10:00:00Z",
  },
];

const PREVIEW = "<!doctype html><html><body><h1>Ada Lovelace</h1></body></html>";

function renderPanel(selectedId: string | null = null) {
  const onSelect = vi.fn();
  const view = renderWithQueryClient(
    <VersionPanel resumeId={RESUME_ID} selectedId={selectedId} onSelect={onSelect} />,
  );
  return { ...view, onSelect };
}

describe("VersionPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.mockResolvedValue(VERSIONS);
    raw.mockResolvedValue(new Response(PREVIEW, { headers: { "Content-Type": "text/html" } }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows nothing at all before the first draft exists", async () => {
    request.mockResolvedValue([]);
    renderPanel();

    await vi.waitFor(() => expect(request).toHaveBeenCalled());
    expect(screen.queryByRole("heading", { name: "Drafts" })).not.toBeInTheDocument();
  });

  it("lists every draft, newest first", async () => {
    renderPanel();

    expect(await screen.findByRole("heading", { name: "Drafts" })).toBeInTheDocument();
    const buttons = screen.getAllByRole("button", { name: /Version/ });
    expect(buttons[0]).toHaveTextContent("Version 2");
    expect(buttons[1]).toHaveTextContent("Version 1");
  });

  it("selects the newest draft when none is chosen", async () => {
    const { onSelect } = renderPanel();

    await vi.waitFor(() => expect(onSelect).toHaveBeenCalledWith(VERSIONS[0].id));
  });

  it("previews the chosen draft in a sandboxed frame", async () => {
    renderPanel(VERSIONS[1].id);

    const frame = await screen.findByTitle("Resume preview");
    expect(frame).toHaveAttribute("sandbox", "");
    expect(frame).toHaveAttribute("srcdoc", PREVIEW);
    expect(raw).toHaveBeenCalledWith(
      `/api/v1/resumes/${RESUME_ID}/versions/${VERSIONS[1].id}/preview`,
      expect.anything(),
    );
  });

  it("switches the preview when another draft is chosen", async () => {
    const { user, onSelect } = renderPanel(VERSIONS[0].id);

    await user.click(await screen.findByRole("button", { name: /Version 1/ }));

    expect(onSelect).toHaveBeenCalledWith(VERSIONS[1].id);
  });

  it("downloads the PDF under the name the API gave it", async () => {
    const click = vi.fn();
    const anchor = { href: "", download: "", click } as unknown as HTMLAnchorElement;
    // Only the download link is faked; React still needs to create real elements.
    const createElement = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) =>
      tag === "a" ? anchor : createElement(tag),
    );
    const createObjectURL = vi.fn(() => "blob:resume");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    raw.mockImplementation(async (path: string) =>
      path.endsWith("/pdf")
        ? new Response(new Blob(["%PDF-1.4"]), {
            headers: { "Content-Disposition": 'attachment; filename="Backend-resume-v2.pdf"' },
          })
        : new Response(PREVIEW),
    );

    const { user } = renderPanel(VERSIONS[0].id);
    await user.click(await screen.findByRole("button", { name: "Download PDF" }));

    await vi.waitFor(() => expect(click).toHaveBeenCalled());
    expect(anchor.download).toBe("Backend-resume-v2.pdf");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:resume");
  });

  it("says so when the preview cannot be loaded", async () => {
    raw.mockRejectedValue(new Error("network"));
    renderPanel(VERSIONS[0].id);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.queryByTitle("Resume preview")).not.toBeInTheDocument();
  });
});
