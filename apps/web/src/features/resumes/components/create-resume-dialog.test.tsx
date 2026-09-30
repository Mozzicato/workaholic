import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { CreateResumeDialog } from "./create-resume-dialog";

const request = vi.fn();
const router = { push: vi.fn() };

vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request }) }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const RESUME_ID = "11111111-1111-4111-8111-111111111111";
const VERSION_ID = "22222222-2222-4222-8222-222222222222";
const JOB_ID = "33333333-3333-4333-8333-333333333333";

const READY = {
  resume_ready: true,
  cover_letter_ready: true,
  items: [{ key: "name", label: "Your name", done: true, hint: "" }],
};

const NOT_READY = {
  resume_ready: false,
  cover_letter_ready: false,
  items: [
    {
      key: "education",
      label: "Your education",
      done: false,
      hint: "Where you studied, or are studying.",
    },
  ],
};

function api(readiness: unknown = READY) {
  request.mockImplementation(async (path: string, options: { method?: string } = {}) => {
    if (path === "/api/v1/profile/readiness") return readiness;
    if (path === "/api/v1/jobs" && options.method === "POST") return { id: JOB_ID, title: "Role" };
    if (path === "/api/v1/resumes" && options.method === "POST") {
      return { id: RESUME_ID, title: "General resume", template: "classic" };
    }
    if (path === `/api/v1/resumes/${RESUME_ID}/versions`) return { id: VERSION_ID };
    if (path.endsWith("/tailored")) return { version: { id: VERSION_ID }, summary: {} };
    throw new Error(`unexpected call: ${options.method ?? "GET"} ${path}`);
  });
}

function calls(method: string, endsWith: string) {
  return request.mock.calls.filter(
    ([path, options]) => String(path).endsWith(endsWith) && (options?.method ?? "GET") === method,
  );
}

async function openDialog() {
  const view = renderWithQueryClient(<CreateResumeDialog />);
  await view.user.click(screen.getByRole("button", { name: "Create" }));
  return view.user;
}

describe("CreateResumeDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("asks what the resume is for, the same as starting from the record", async () => {
    api();
    await openDialog();

    expect(await screen.findByText("What is it for?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /A general resume/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /For a specific job/ })).toBeInTheDocument();
  });

  it("writes a general resume in the chosen template and opens it", async () => {
    api();
    const user = await openDialog();

    await user.click(await screen.findByRole("radio", { name: /Harvard/ }));
    await user.click(screen.getByRole("button", { name: /Write it in Harvard/ }));

    await vi.waitFor(() => expect(router.push).toHaveBeenCalledWith(`/resumes/${RESUME_ID}`));
    expect(calls("POST", "/api/v1/resumes")[0][1].body).toMatchObject({
      title: "General resume",
      template: "harvard",
      target_role: null,
    });
    // The draft is written here; nobody has to find another button for it.
    expect(calls("POST", `/resumes/${RESUME_ID}/versions`)).toHaveLength(1);
  });

  it("reads the advert and leads with what that job asks for", async () => {
    api();
    const user = await openDialog();

    await user.click(await screen.findByRole("button", { name: /For a specific job/ }));
    await user.type(screen.getByLabelText("Role"), "Junior Frontend Engineer");
    await user.type(
      screen.getByLabelText("Paste the job advert"),
      "We want a junior frontend engineer comfortable with React and TypeScript.",
    );
    await user.click(screen.getByRole("button", { name: "Write it for this job" }));

    await vi.waitFor(() => expect(router.push).toHaveBeenCalledWith(`/resumes/${RESUME_ID}`));
    expect(calls("POST", "/api/v1/jobs")).toHaveLength(1);
    expect(calls("POST", "/tailored")).toHaveLength(1);
  });

  it("will not write from a record that is not ready, and says what is missing", async () => {
    api(NOT_READY);
    await openDialog();

    expect(await screen.findByText(/Where you studied/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Write it in/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Answer a few questions" })).toBeInTheDocument();
  });

  it("asks a letter who it is for, and writes it there and then", async () => {
    api();
    const user = await openDialog();

    await user.click(screen.getByRole("button", { name: /Cover letter/ }));
    await user.type(await screen.findByLabelText("Company"), "Northwind Payments");
    await user.type(screen.getByLabelText("Role (optional)"), "Junior Frontend Engineer");
    await user.type(
      screen.getByLabelText("Paste the job advert (optional)"),
      "We want a junior frontend engineer comfortable with React and TypeScript.",
    );
    await user.click(screen.getByRole("button", { name: "Write my letter" }));

    await vi.waitFor(() => expect(router.push).toHaveBeenCalledWith(`/resumes/${RESUME_ID}`));
    expect(calls("POST", "/api/v1/resumes")[0][1].body).toMatchObject({
      title: "Northwind Payments letter",
      document_type: "cover_letter",
      target_role: "Junior Frontend Engineer",
    });
    // Written immediately, with the advert deciding what leads.
    const written = calls("POST", `/resumes/${RESUME_ID}/versions`);
    expect(written).toHaveLength(1);
    expect(written[0][1].body.brief).toMatchObject({ company: "Northwind Payments" });
    // The advert is kept as a job, so matching and coaching come with it.
    expect(calls("POST", "/api/v1/jobs")).toHaveLength(1);
  });

  it("will not write a letter without knowing who it is to", async () => {
    api();
    const user = await openDialog();

    await user.click(screen.getByRole("button", { name: /Cover letter/ }));

    expect(await screen.findByLabelText("Company")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Write my letter" })).toBeDisabled();
  });

  it("does not tailor from a couple of words", async () => {
    api();
    const user = await openDialog();

    await user.click(await screen.findByRole("button", { name: /For a specific job/ }));
    await user.type(screen.getByLabelText("Paste the job advert"), "frontend role");

    expect(screen.getByRole("button", { name: "Write it for this job" })).toBeDisabled();
  });
});
