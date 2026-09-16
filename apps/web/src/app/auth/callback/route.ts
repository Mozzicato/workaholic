import type { EmailOtpType } from "@supabase/supabase-js";
import { NextResponse, type NextRequest } from "next/server";

import { routes, safeNextPath } from "@/lib/routes";
import { createClient } from "@/lib/supabase/server";

/**
 * Completes every link-based sign-in: Google OAuth, email confirmation and password
 * recovery. Supports both the PKCE `code` flow and `token_hash` email templates.
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl;
  const code = searchParams.get("code");
  const tokenHash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const next = safeNextPath(searchParams.get("next"));

  const supabase = await createClient();
  let failed = true;

  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    failed = Boolean(error);
  } else if (tokenHash && type) {
    const { error } = await supabase.auth.verifyOtp({ type, token_hash: tokenHash });
    failed = Boolean(error);
  }

  if (failed) {
    const reason = searchParams.get("error_description") ? "provider" : "link";
    return NextResponse.redirect(new URL(`${routes.login}?error=${reason}`, origin));
  }

  const destination = type === "recovery" ? routes.resetPassword : next;
  return NextResponse.redirect(new URL(destination, origin));
}
