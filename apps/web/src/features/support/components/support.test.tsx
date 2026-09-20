import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { AdminView } from "./admin-view";
import { FeedbackButton } from "./feedback-button";
import { SendTemplateButton } from "./send-template";

const request = vi.fn();
const upload = vi.fn();
const { toastSuccess, toastError } = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request, upload }) }));
vi.mock("sonner", () => ({ toast: { success: toastSuccess, error: toastError } }));
vi.mock("next/navigation", () => ({ usePathname: () => "/assistant" }));

const STATS = {
  generated_at: "2026-09-20T10:00:00Z",
  users_total: 12,
  users_last_7_days: 3,
  users_last_30_days: 9,
  records_ready_for_a_resume: 5,
  resumes_total: 7,
  letters_total: 2,
  drafts_total: 11,
  drafts_last_7_days: 4,
  interviews_started: 8,
  interviews_completed: 6,
  documents_imported: 3,
  jobs_saved: 1,
  wrote_a_draft_last_7_days: 4,
  used_the_assistant_last_7_days: 2,
  feedback_new: 1,
  template_requests_new: 1,
  templates_in_use: [{ label: "classic", count: 5 }],
  signups_by_day: [{ label: "2026-09-19", count: 2 }],
};

const FEEDBACK = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "ada@example.com",
  message: "The mic button is hard to find",
  page: "/assistant",
  status: "new",
  created_at: "2026-09-20T09:00:00Z",
  handled_at: null,
};

const TEMPLATE_REQUEST = {
  id: "22222222-2222-4222-8222-222222222222",
  email: "ada@example.com",
  note: "my school uses this",
  filename: "school.pdf",
  content_type: "application/pdf",
  size_bytes: 20480,
  status: "new",
  created_at: "2026-09-20T09:00:00Z",
  handled_at: null,
};

function admin(isAdmin: boolean) {
  request.mockImplementation(async (path: string) => {
    if (path === "/api/v1/me") return { is_admin: isAdmin, email: "boss@workaholic.dev" };
    if (path === "/api/v1/admin/stats") return STATS;
    if (path === "/api/v1/admin/feedback") return [FEEDBACK];
    if (path === "/api/v1/admin/template-requests") return [TEMPLATE_REQUEST];
    if (path === "/api/v1/admin/users") return [];
    throw new Error(`unexpected call: ${path}`);
  });
}

describe("FeedbackButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends the message with the page it was written on", async () => {
    request.mockResolvedValue(FEEDBACK);
    const { user } = renderWithQueryClient(<FeedbackButton />);

    await user.click(screen.getByRole("button", { name: "Feedback" }));
    await user.type(screen.getByLabelText("Your message"), "The mic button is hard to find");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await vi.waitFor(() => expect(request).toHaveBeenCalled());
    expect(request.mock.calls[0][0]).toBe("/api/v1/feedback");
    expect(request.mock.calls[0][1].body).toEqual({
      message: "The mic button is hard to find",
      page: "/assistant",
    });
  });

  it("will not send an empty message", async () => {
    const { user } = renderWithQueryClient(<FeedbackButton />);

    await user.click(screen.getByRole("button", { name: "Feedback" }));

    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
    expect(request).not.toHaveBeenCalled();
  });
});

describe("SendTemplateButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("says plainly that a person builds it, and does not promise every design", async () => {
    const { user } = renderWithQueryClient(<SendTemplateButton />);

    await user.click(screen.getByRole("button", { name: /Have your own template/ }));

    expect(screen.getByText(/We do this by hand/)).toBeInTheDocument();
    expect(screen.getByText(/cannot promise every design/)).toBeInTheDocument();
    expect(screen.getByText(/never read into your record/)).toBeInTheDocument();
  });

  it("sends the file with the note", async () => {
    upload.mockResolvedValue(TEMPLATE_REQUEST);
    const { user } = renderWithQueryClient(<SendTemplateButton />);
    await user.click(screen.getByRole("button", { name: /Have your own template/ }));

    const file = new File(["%PDF"], "school.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText("Choose a template file"), file);
    await user.type(screen.getByLabelText(/Anything we should know/), "my school uses this");
    await user.click(screen.getByRole("button", { name: "Send template" }));

    await vi.waitFor(() => expect(upload).toHaveBeenCalled());
    const form = upload.mock.calls[0][1] as FormData;
    expect((form.get("file") as File).name).toBe("school.pdf");
    expect(form.get("note")).toBe("my school uses this");
  });

  it("cannot be sent without a file", async () => {
    const { user } = renderWithQueryClient(<SendTemplateButton />);

    await user.click(screen.getByRole("button", { name: /Have your own template/ }));

    expect(screen.getByRole("button", { name: "Send template" })).toBeDisabled();
  });
});

describe("AdminView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("turns away an account that is not an administrator", async () => {
    admin(false);
    renderWithQueryClient(<AdminView />);

    expect(await screen.findByText("Administrators only")).toBeInTheDocument();
    expect(request).not.toHaveBeenCalledWith("/api/v1/admin/users", expect.anything());
  });

  it("shows how the product is being used", async () => {
    admin(true);
    renderWithQueryClient(<AdminView />);

    expect(await screen.findByRole("heading", { name: "Accounts" })).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument(); // accounts
    expect(screen.getByText("Records ready for a resume")).toBeInTheDocument();
    expect(screen.getByText("of 12 accounts")).toBeInTheDocument();
  });

  it("names templates as people see them, not as the database does", async () => {
    admin(true);
    renderWithQueryClient(<AdminView />);

    expect(await screen.findByText("Classic")).toBeInTheDocument();
    expect(screen.queryByText("classic")).not.toBeInTheDocument();
  });

  it("shows what people sent in", async () => {
    admin(true);
    renderWithQueryClient(<AdminView />);

    expect(await screen.findByText("The mic button is hard to find")).toBeInTheDocument();
    expect(screen.getByText("school.pdf")).toBeInTheDocument();
    expect(screen.getByText("my school uses this")).toBeInTheDocument();
  });
});
