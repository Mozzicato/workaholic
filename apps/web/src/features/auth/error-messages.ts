const FALLBACK = "Something went wrong. Please try again.";

const MESSAGES: Record<string, string> = {
  invalid_credentials: "That email and password don't match. Check them and try again.",
  email_not_confirmed: "Confirm your email address first — the link is in your inbox.",
  user_already_exists: "An account with this email already exists. Try signing in instead.",
  email_exists: "An account with this email already exists. Try signing in instead.",
  weak_password: "Choose a stronger password — mix words, numbers and symbols.",
  same_password: "Your new password must be different from your current one.",
  email_address_invalid: "That email address can't receive mail. Try another one.",
  over_email_send_rate_limit:
    "We've sent too many emails to this address recently. Wait a few minutes and try again.",
  over_request_rate_limit: "Too many attempts. Wait a minute and try again.",
  signup_disabled: "New sign-ups are paused right now. Please try again later.",
  session_not_found: "Your session has ended. Please sign in again.",
  otp_expired: "That link has expired. Request a new one.",
};

/** Links that bring users back to /login?error=… */
export const CALLBACK_ERROR_MESSAGES: Record<string, string> = {
  link: "That link is invalid or has expired. Please try again.",
  provider: "We couldn't complete sign-in with that provider. Please try again.",
};

type MaybeAuthError = { code?: string; status?: number; name?: string } | null | undefined;

export function authErrorMessage(error: MaybeAuthError): string {
  if (!error) return FALLBACK;
  if (error.code && MESSAGES[error.code]) return MESSAGES[error.code];
  if (error.name === "AuthRetryableFetchError" || error.status === 0) {
    return "We couldn't reach the sign-in service. Check your connection and try again.";
  }
  return FALLBACK;
}
