import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { InterviewView } from "./interview-view";

const request = vi.fn();
const { toastError } = vi.hoisted(() => ({ toastError: vi.fn() }));

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request }) }));
vi.mock("sonner", () => ({ toast: { error: toastError, success: vi.fn() } }));

const RESUME_ID = "11111111-1111-4111-8111-111111111111";
const SESSION_ID = "22222222-2222-4222-8222-222222222222";

const RESUME = {
  id: RESUME_ID,
  title: "Backend resume",
  target_role: "Junior Backend Engineer",
  document_type: "resume",
  template: "classic",
  status: "draft",
  current_version_id: null,
  created_at: "2026-09-18T10:00:00Z",
  updated_at: "2026-09-18T10:00:00Z",
};

function message(id: string, role: "agent" | "user", content: string, sequence: number) {
  return { id, sequence, role, content, created_at: "2026-09-18T10:00:00Z" };
}

const SESSION = {
  id: SESSION_ID,
  resume_id: RESUME_ID,
  target_role: "Junior Backend Engineer",
  status: "active",
  questions_asked: 1,
  completed_at: null,
  created_at: "2026-09-18T10:00:00Z",
  updated_at: "2026-09-18T10:00:00Z",
};

const FIRST_QUESTION = message("m1", "agent", "Where have you worked most recently?", 1);

/** Routes every call the page makes to the right canned response. */
function api(overrides: Partial<Record<string, unknown>> = {}) {
  request.mockImplementation(async (path: string, options: { method?: string } = {}) => {
    if (path === `/api/v1/resumes/${RESUME_ID}`) return overrides.resume ?? RESUME;
    if (path === "/api/v1/interviews" && options.method === "POST") {
      return overrides.start ?? { session: SESSION, messages: [FIRST_QUESTION] };
    }
    if (path === `/api/v1/interviews/${SESSION_ID}`) {
      return overrides.transcript ?? { session: SESSION, messages: [FIRST_QUESTION] };
    }
    if (path === `/api/v1/interviews/${SESSION_ID}/answers`) return overrides.turn;
    if (path === `/api/v1/interviews/${SESSION_ID}/abandon`) {
      return { ...SESSION, status: "abandoned" };
    }
    throw new Error(`unexpected call: ${options.method ?? "GET"} ${path}`);
  });
}

describe("InterviewView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts an interview for the resume and shows the first question", async () => {
    api();
    renderWithQueryClient(<InterviewView resumeId={RESUME_ID} />);

    expect(await screen.findByText("Where have you worked most recently?")).toBeInTheDocument();
    expect(request).toHaveBeenCalledWith(
      "/api/v1/interviews",
      expect.objectContaining({
        method: "POST",
        body: { resume_id: RESUME_ID, target_role: "Junior Backend Engineer" },
      }),
    );
  });

  it("sends an answer and shows what went into the record", async () => {
    api({
      turn: {
        session: { ...SESSION, questions_asked: 2 },
        reply: message("m3", "agent", "What did you do there?", 3),
        recorded: ["Backend Engineer Intern at Lumen Freight"],
        dropped: [],
        completed: false,
      },
      transcript: {
        session: SESSION,
        messages: [
          FIRST_QUESTION,
          message("m2", "user", "I interned at Lumen Freight", 2),
          message("m3", "agent", "What did you do there?", 3),
        ],
      },
    });
    const { user } = renderWithQueryClient(<InterviewView resumeId={RESUME_ID} />);

    await user.type(await screen.findByLabelText("Your answer"), "I interned at Lumen Freight");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Backend Engineer Intern at Lumen Freight")).toBeInTheDocument();
    expect(screen.getByText("What did you do there?")).toBeInTheDocument();
  });

  it("says plainly what it refused to record", async () => {
    api({
      turn: {
        session: SESSION,
        reply: message("m3", "agent", "Where was that?", 3),
        recorded: [],
        dropped: ["Google", "Senior Engineer"],
        completed: false,
      },
      transcript: {
        session: SESSION,
        messages: [
          FIRST_QUESTION,
          message("m2", "user", "I did an internship", 2),
          message("m3", "agent", "Where was that?", 3),
        ],
      },
    });
    const { user } = renderWithQueryClient(<InterviewView resumeId={RESUME_ID} />);

    await user.type(await screen.findByLabelText("Your answer"), "I did an internship");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByText(/Left out, because you didn't say it: Google; Senior Engineer/),
    ).toBeInTheDocument();
  });

  it("keeps the answer in the box when sending fails", async () => {
    api({ turn: undefined });
    request.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      if (path === `/api/v1/resumes/${RESUME_ID}`) return RESUME;
      if (path === "/api/v1/interviews" && options.method === "POST") {
        return { session: SESSION, messages: [FIRST_QUESTION] };
      }
      if (path === `/api/v1/interviews/${SESSION_ID}`) {
        return { session: SESSION, messages: [FIRST_QUESTION] };
      }
      throw new Error("the network is down");
    });
    const { user } = renderWithQueryClient(<InterviewView resumeId={RESUME_ID} />);

    const box = await screen.findByLabelText("Your answer");
    await user.type(box, "something I would hate to lose");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await vi.waitFor(() => expect(toastError).toHaveBeenCalled());
    expect(box).toHaveValue("something I would hate to lose");
  });

  it("offers the way onward once the interview is finished", async () => {
    api({
      transcript: {
        session: { ...SESSION, status: "completed" },
        messages: [FIRST_QUESTION, message("m2", "agent", "That's enough to work with.", 2)],
      },
    });
    renderWithQueryClient(<InterviewView resumeId={RESUME_ID} />);

    expect(await screen.findByRole("link", { name: "Review my record" })).toHaveAttribute(
      "href",
      "/profile",
    );
    expect(screen.queryByLabelText("Your answer")).not.toBeInTheDocument();
  });

  it("does not send an empty answer", async () => {
    api();
    const { user } = renderWithQueryClient(<InterviewView resumeId={RESUME_ID} />);

    await screen.findByLabelText("Your answer");
    const send = screen.getByRole("button", { name: "Send" });

    expect(send).toBeDisabled();
    await user.click(send);
    expect(request).not.toHaveBeenCalledWith(
      `/api/v1/interviews/${SESSION_ID}/answers`,
      expect.anything(),
    );
  });
});
