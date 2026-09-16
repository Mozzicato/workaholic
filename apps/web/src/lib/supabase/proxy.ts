import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

import { env } from "@/lib/env";
import { SIGNED_OUT_ONLY_PATHS, isProtectedPath, loginPathFor, routes } from "@/lib/routes";

/**
 * Refreshes the Supabase session cookie on every matched request and applies coarse
 * route gating. This is a convenience layer only: protected layouts verify the user
 * again, and the API verifies the access token on every call.
 */
export async function updateSession(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    env.NEXT_PUBLIC_SUPABASE_URL,
    env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  // Do not add code between client creation and getClaims(): the session refresh
  // must happen first or users can be signed out unexpectedly.
  const { data } = await supabase.auth.getClaims();
  const isSignedIn = Boolean(data?.claims);
  const { pathname, search } = request.nextUrl;

  if (!isSignedIn && isProtectedPath(pathname)) {
    return redirectPreservingCookies(request, response, loginPathFor(`${pathname}${search}`));
  }

  if (isSignedIn && (SIGNED_OUT_ONLY_PATHS as readonly string[]).includes(pathname)) {
    return redirectPreservingCookies(request, response, routes.dashboard);
  }

  return response;
}

function redirectPreservingCookies(
  request: NextRequest,
  sessionResponse: NextResponse,
  destination: string,
) {
  const redirect = NextResponse.redirect(new URL(destination, request.url));
  // Carry refreshed session cookies across the redirect so the browser and server stay in sync.
  sessionResponse.cookies.getAll().forEach((cookie) => redirect.cookies.set(cookie));
  return redirect;
}
