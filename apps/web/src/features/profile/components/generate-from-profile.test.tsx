import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { GenerateFromProfile } from "./generate-from-profile";

const request = vi.fn();
const push = vi.fn();

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request, upload: vi.fn() }) }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

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
      key: "experience_or_projects",
      label: "Something you've done",
      done: false,
      hint: "A job, internship or project, with at least one line about what you did.",
    },
  ],
};

function api(readiness: unknown) {
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

describe("GenerateFromProfile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("writes a general resume without leaving the page", async () => {
    api(READY);
    const { user } = renderWithQueryClient(<GenerateFromProfile />);

    await user.click(await screen.findByRole("button", { name: /Generate my resume/ }));
    await user.click(screen.getByRole("button", { name: "Write it" }));

    await vi.waitFor(() => expect(push).toHaveBeenCalledWith(`/resumes/${RESUME_ID}`));
    expect(calls("POST", "/api/v1/resumes")[0][1].body).toMatchObject({
      title: "General resume",
      target_role: null,
    });
    expect(calls("POST", "/api/v1/jobs")).toHaveLength(0);
  });

  it("reads the advert, writes, then leads with what that job asks for", async () => {
    api(READY);
    const { user } = renderWithQueryClient(<GenerateFromProfile />);

    await user.click(await screen.findByRole("button", { name: /Generate my resume/ }));
    await user.click(screen.getByRole("button", { name: /For a specific job/ }));
    await user.type(screen.getByLabelText("Role"), "Junior Frontend Engineer");
    await user.type(screen.getByLabelText("Company (optional)"), "Northwind Payments");
    await user.type(
      screen.getByLabelText("Paste the job advert"),
      "We are looking for a junior frontend engineer comfortable with React and TypeScript.",
    );
    await user.click(screen.getByRole("button", { name: "Write it" }));

    await vi.waitFor(() => expect(push).toHaveBeenCalledWith(`/resumes/${RESUME_ID}`));
    expect(calls("POST", "/api/v1/jobs")).toHaveLength(1);
    expect(calls("POST", "/api/v1/resumes")[0][1].body).toMatchObject({
      title: "Junior Frontend Engineer — Northwind Payments",
      target_role: "Junior Frontend Engineer",
    });
    expect(calls("POST", "/tailored")).toHaveLength(1);
  });

  it("will not write from a record that is not ready, and says what is missing", async () => {
    api(NOT_READY);
    renderWithQueryClient(<GenerateFromProfile />);

    expect(await screen.findByText("Not quite ready yet")).toBeInTheDocument();
    expect(screen.getByText(/A job, internship or project/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Generate my resume/ })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: /Answer a few questions instead/ }),
    ).toBeInTheDocument();
  });

  it("does not write a tailored resume from a couple of words", async () => {
    api(READY);
    const { user } = renderWithQueryClient(<GenerateFromProfile />);

    await user.click(await screen.findByRole("button", { name: /Generate my resume/ }));
    await user.click(screen.getByRole("button", { name: /For a specific job/ }));
    await user.type(screen.getByLabelText("Paste the job advert"), "frontend role");

    expect(screen.getByRole("button", { name: "Write it" })).toBeDisabled();
  });
});
