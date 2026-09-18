import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { AssistantView } from "./assistant-view";

const request = vi.fn();
const upload = vi.fn();
const { toastError } = vi.hoisted(() => ({ toastError: vi.fn() }));

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request, upload }) }));
vi.mock("sonner", () => ({ toast: { error: toastError, success: vi.fn() } }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const SESSION_ID = "33333333-3333-4333-8333-333333333333";
const EARLIER_ID = "44444444-4444-4444-8444-444444444444";

function message(id: string, role: "agent" | "user", content: string, sequence: number) {
  return { id, sequence, role, content, created_at: "2026-09-19T10:00:00Z" };
}

function session(id: string, status = "active") {
  return {
    id,
    resume_id: null,
    target_role: null,
    status,
    questions_asked: 1,
    completed_at: null,
    created_at: "2026-09-19T10:00:00Z",
    updated_at: "2026-09-19T10:00:00Z",
  };
}

const GREETING = message(
  "m1",
  "agent",
  "Hi! I'll walk you through your resume one question at a time.\n\nWhat's your full name?",
  1,
);
const AFTER_UPLOAD = message(
  "m2",
  "agent",
  "Thanks — I've added what you confirmed from your document.\n\nWhat grade or CGPA do you have?",
  2,
);

const NOT_READY = {
  resume_ready: false,
  cover_letter_ready: false,
  items: [
    { key: "name", label: "Your name", done: false, hint: "The name at the top of the page." },
    { key: "education", label: "Your education", done: false, hint: "Where you studied." },
  ],
};

const PROPOSAL = {
  kind: "pdf",
  pages: 1,
  prompt_version: "documents.parse.v2",
  model: "gpt-5-mini",
  dropped: [],
  contents: {
    full_name: "Ada Lovelace",
    email: "ada@example.com",
    phone: "",
    location: "",
    headline: "",
    summary: "",
    roles: [],
    projects: [],
    education: [
      {
        institution: "University of Lagos",
        qualification: "BSc",
        field_of_study: "",
        start_date: "",
        end_date: "",
        grade: "",
      },
    ],
    skills: [],
  },
};

function api({ earlier = [] as unknown[] } = {}) {
  let transcript = { session: session(SESSION_ID), messages: [GREETING] };
  request.mockImplementation(async (path: string, options: { method?: string } = {}) => {
    if (path === "/api/v1/profile/readiness") return NOT_READY;
    if (path === "/api/v1/interviews" && options.method === "POST") return transcript;
    if (path === "/api/v1/interviews") return earlier;
    if (path === `/api/v1/interviews/${SESSION_ID}`) return transcript;
    if (path === `/api/v1/interviews/${EARLIER_ID}`) {
      return { session: session(EARLIER_ID), messages: [GREETING] };
    }
    if (path === "/api/v1/documents/import/accept") return { added: ["University of Lagos"] };
    if (path === `/api/v1/interviews/${SESSION_ID}/continue`) {
      transcript = { ...transcript, messages: [GREETING, AFTER_UPLOAD] };
      return {
        session: session(SESSION_ID),
        reply: AFTER_UPLOAD,
        recorded: [],
        dropped: [],
        completed: false,
      };
    }
    throw new Error(`unexpected call: ${options.method ?? "GET"} ${path}`);
  });
}

const spoken: string[] = [];
const speech = { speak: vi.fn(), cancel: vi.fn() };

class FakeUtterance {
  text: string;
  lang = "";
  rate = 1;
  onstart: (() => void) | null = null;
  onend: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(text: string) {
    this.text = text;
  }
}

describe("AssistantView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    spoken.length = 0;
    Element.prototype.scrollIntoView = vi.fn();
    speech.speak.mockImplementation((utterance: FakeUtterance) => spoken.push(utterance.text));
    Object.defineProperty(window, "speechSynthesis", { value: speech, configurable: true });
    vi.stubGlobal("SpeechSynthesisUtterance", FakeUtterance);
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    // Removed so other suites see a browser without speech, as jsdom is.
    Reflect.deleteProperty(window, "speechSynthesis");
  });

  it("shows what a resume needs before anything starts", async () => {
    api();
    renderWithQueryClient(<AssistantView />);

    expect(await screen.findByText("Your education")).toBeInTheDocument();
    expect(screen.getByText("Where you studied.")).toBeInTheDocument();
    // Nothing starts until they press Start: a browser only lets a page speak after a click.
    expect(request).not.toHaveBeenCalledWith(
      "/api/v1/interviews",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("starts a conversation of its own, not tied to a resume", async () => {
    api();
    const { user } = renderWithQueryClient(<AssistantView />);

    await user.click(await screen.findByRole("button", { name: "Start" }));

    expect(await screen.findByText(/What's your full name\?/)).toBeInTheDocument();
    expect(request).toHaveBeenCalledWith(
      "/api/v1/interviews",
      expect.objectContaining({ method: "POST", body: {} }),
    );
  });

  it("reads each question aloud as it arrives", async () => {
    api();
    const { user } = renderWithQueryClient(<AssistantView />);

    await user.click(await screen.findByRole("button", { name: "Start" }));

    await vi.waitFor(() => expect(spoken).toEqual([GREETING.content]));
  });

  it("stays quiet once reading aloud is switched off", async () => {
    api();
    const { user } = renderWithQueryClient(<AssistantView />);

    await user.click(await screen.findByRole("button", { name: "Reading questions aloud" }));
    await user.click(screen.getByRole("button", { name: "Start" }));

    await screen.findByText(/What's your full name\?/);
    expect(speech.speak).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Read questions aloud" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("offers back an unfinished conversation", async () => {
    api({ earlier: [session(EARLIER_ID)] });
    const { user } = renderWithQueryClient(<AssistantView />);

    await user.click(await screen.findByRole("button", { name: "Pick up where we left off" }));

    expect(await screen.findByText(/What's your full name\?/)).toBeInTheDocument();
    expect(request).not.toHaveBeenCalledWith(
      "/api/v1/interviews",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("takes a CV part-way through, then asks only what it didn't cover", async () => {
    api();
    upload.mockResolvedValue(PROPOSAL);
    const { user } = renderWithQueryClient(<AssistantView />);
    await user.click(await screen.findByRole("button", { name: "Start" }));
    await screen.findByText(/What's your full name\?/);

    await user.click(screen.getByRole("button", { name: "Upload a CV" }));
    const file = new File(["%PDF"], "cv.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText("Choose a resume to upload"), file);
    await user.click(await screen.findByRole("button", { name: "Add 1 to my record" }));

    expect(await screen.findByText(/What grade or CGPA do you have\?/)).toBeInTheDocument();
    expect(request).toHaveBeenCalledWith(
      `/api/v1/interviews/${SESSION_ID}/continue`,
      expect.objectContaining({ method: "POST" }),
    );
    // Back to answering, with the answer box in place of the upload.
    expect(screen.getByLabelText("Your answer")).toBeInTheDocument();
  });
});
