import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "./login-form";

const router = { replace: vi.fn(), refresh: vi.fn() };
const signInWithPassword = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ auth: { signInWithPassword } }),
}));

function renderForm(props: Partial<Parameters<typeof LoginForm>[0]> = {}) {
  render(<LoginForm next="/dashboard" googleEnabled={false} {...props} />);
  return userEvent.setup();
}

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("validates before contacting the auth service", async () => {
    const user = renderForm();

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Enter your email address")).toBeInTheDocument();
    expect(screen.getByText("Enter your password")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    expect(signInWithPassword).not.toHaveBeenCalled();
  });

  it("rejects a malformed email address", async () => {
    const user = renderForm();

    await user.type(screen.getByLabelText("Email"), "not-an-email");
    await user.type(screen.getByLabelText("Password"), "hunter22");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Enter a valid email address")).toBeInTheDocument();
    expect(signInWithPassword).not.toHaveBeenCalled();
  });

  it("signs in and continues to the requested page", async () => {
    signInWithPassword.mockResolvedValue({ data: {}, error: null });
    const user = renderForm({ next: "/resumes/42" });

    await user.type(screen.getByLabelText("Email"), "  ada@example.com ");
    await user.type(screen.getByLabelText("Password"), "correct horse");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await vi.waitFor(() => expect(router.replace).toHaveBeenCalledWith("/resumes/42"));
    expect(signInWithPassword).toHaveBeenCalledWith({ email: "ada@example.com", password: "correct horse" });
    expect(router.refresh).toHaveBeenCalled();
  });

  it("explains a failed sign-in in plain language", async () => {
    signInWithPassword.mockResolvedValue({
      data: {},
      error: { code: "invalid_credentials", status: 400, name: "AuthApiError" },
    });
    const user = renderForm();

    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That email and password don't match. Check them and try again.",
    );
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("shows errors passed back from an expired sign-in link", () => {
    renderForm({ initialError: "That link is invalid or has expired. Please try again." });

    expect(screen.getByRole("alert")).toHaveTextContent("That link is invalid or has expired.");
  });

  it("lets people reveal the password they typed", async () => {
    const user = renderForm();
    const password = screen.getByLabelText("Password");

    expect(password).toHaveAttribute("type", "password");
    await user.click(screen.getByRole("button", { name: "Show password" }));
    expect(password).toHaveAttribute("type", "text");
  });
});
