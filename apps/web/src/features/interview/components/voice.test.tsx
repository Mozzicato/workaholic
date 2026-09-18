import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { InterviewView } from "./interview-view";

const request = vi.fn();
const upload = vi.fn();
const { toastError } = vi.hoisted(() => ({ toastError: vi.fn() }));

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request, upload }) }));
vi.mock("sonner", () => ({ toast: { error: toastError, success: vi.fn() } }));

const RESUME_ID = "11111111-1111-4111-8111-111111111111";
const SESSION_ID = "22222222-2222-4222-8222-222222222222";

const SESSION = {
  id: SESSION_ID,
  resume_id: RESUME_ID,
  target_role: null,
  status: "active",
  questions_asked: 1,
  completed_at: null,
  created_at: "2026-09-18T10:00:00Z",
  updated_at: "2026-09-18T10:00:00Z",
};

const QUESTION = {
  id: "m1",
  sequence: 1,
  role: "agent",
  content: "Where have you worked most recently?",
  created_at: "2026-09-18T10:00:00Z",
};

/** A MediaRecorder that produces one blob when stopped. */
class FakeMediaRecorder {
  static isTypeSupported = vi.fn(() => true);
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  state: "inactive" | "recording" = "inactive";
  stream = { getTracks: () => [{ stop: vi.fn() }] };

  constructor(
    _stream: unknown,
    readonly options: { mimeType: string },
  ) {}

  get mimeType() {
    return this.options.mimeType;
  }

  start() {
    this.state = "recording";
  }

  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["audio"], { type: this.mimeType }) });
    this.onstop?.();
  }
}

function withApi() {
  request.mockImplementation(async (path: string, options: { method?: string } = {}) => {
    if (path === `/api/v1/resumes/${RESUME_ID}`) {
      return {
        id: RESUME_ID,
        title: "Backend resume",
        target_role: null,
        document_type: "resume",
        status: "draft",
        current_version_id: null,
        created_at: "2026-09-18T10:00:00Z",
        updated_at: "2026-09-18T10:00:00Z",
      };
    }
    if (path === "/api/v1/interviews" && options.method === "POST") {
      return { session: SESSION, messages: [QUESTION] };
    }
    if (path === `/api/v1/interviews/${SESSION_ID}`) {
      return { session: SESSION, messages: [QUESTION] };
    }
    throw new Error(`unexpected call: ${path}`);
  });
}

describe("answering by voice", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
    vi.stubGlobal("MediaRecorder", FakeMediaRecorder);
    vi.stubGlobal("navigator", {
      ...navigator,
      mediaDevices: { getUserMedia: vi.fn(async () => ({ getTracks: () => [] })) },
    });
    withApi();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("puts what was heard into the box rather than sending it", async () => {
    upload.mockResolvedValue({ text: "i interned at lumen freight" });
    const { user } = renderWithQueryClient(<InterviewView resumeId={RESUME_ID} />);

    await user.click(await screen.findByRole("button", { name: "Answer by speaking" }));
    await user.click(await screen.findByRole("button", { name: "Stop recording" }));

    const box = await screen.findByLabelText("Your answer");
    await vi.waitFor(() => expect(box).toHaveValue("i interned at lumen freight"));
    expect(request).not.toHaveBeenCalledWith(
      `/api/v1/interviews/${SESSION_ID}/answers`,
      expect.anything(),
    );
  });

  it("uploads the recording as audio", async () => {
    upload.mockResolvedValue({ text: "heard" });
    const { user } = renderWithQueryClient(<InterviewView resumeId={RESUME_ID} />);

    await user.click(await screen.findByRole("button", { name: "Answer by speaking" }));
    await user.click(await screen.findByRole("button", { name: "Stop recording" }));

    await vi.waitFor(() => expect(upload).toHaveBeenCalled());
    const [path, form] = upload.mock.calls[0];
    expect(path).toBe(`/api/v1/interviews/${SESSION_ID}/transcriptions`);
    expect(form).toBeInstanceOf(FormData);
    expect((form as FormData).get("audio")).toBeInstanceOf(Blob);
  });

  it("adds to what is already typed instead of replacing it", async () => {
    upload.mockResolvedValue({ text: "and I wrote the tests" });
    const { user } = renderWithQueryClient(<InterviewView resumeId={RESUME_ID} />);

    await user.type(await screen.findByLabelText("Your answer"), "I fixed the import job");
    await user.click(screen.getByRole("button", { name: "Answer by speaking" }));
    await user.click(await screen.findByRole("button", { name: "Stop recording" }));

    await vi.waitFor(() =>
      expect(screen.getByLabelText("Your answer")).toHaveValue(
        "I fixed the import job and I wrote the tests",
      ),
    );
  });

  it("tells the user to type when the microphone is refused", async () => {
    vi.stubGlobal("navigator", {
      ...navigator,
      mediaDevices: {
        getUserMedia: vi.fn(async () => {
          throw new DOMException("denied", "NotAllowedError");
        }),
      },
    });
    const { user } = renderWithQueryClient(<InterviewView resumeId={RESUME_ID} />);

    await user.click(await screen.findByRole("button", { name: "Answer by speaking" }));

    await vi.waitFor(() =>
      expect(toastError).toHaveBeenCalledWith(
        "We couldn't use your microphone. You can type your answer instead.",
      ),
    );
    expect(screen.getByLabelText("Your answer")).toBeEnabled();
  });

  it("reports a transcription failure and keeps the box usable", async () => {
    upload.mockRejectedValue(new Error("service down"));
    const { user } = renderWithQueryClient(<InterviewView resumeId={RESUME_ID} />);

    await user.click(await screen.findByRole("button", { name: "Answer by speaking" }));
    await user.click(await screen.findByRole("button", { name: "Stop recording" }));

    await vi.waitFor(() => expect(toastError).toHaveBeenCalled());
    expect(screen.getByLabelText("Your answer")).toBeEnabled();
  });

  it("hides the microphone in a browser that cannot record", async () => {
    vi.stubGlobal("MediaRecorder", undefined);
    renderWithQueryClient(<InterviewView resumeId={RESUME_ID} />);

    await screen.findByLabelText("Your answer");
    expect(screen.queryByRole("button", { name: "Answer by speaking" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();
  });
});
