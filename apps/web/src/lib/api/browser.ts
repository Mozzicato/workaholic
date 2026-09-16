"use client";

import { env } from "@/lib/env";
import { createClient } from "@/lib/supabase/client";

import { createApiClient, type ApiClient } from "./client";

let browserApiClient: ApiClient | undefined;

/** Shared API client for Client Components, authenticated with the browser session. */
export function getApiClient(): ApiClient {
  browserApiClient ??= createApiClient({
    baseUrl: env.NEXT_PUBLIC_API_URL,
    async getAccessToken() {
      const { data } = await createClient().auth.getSession();
      return data.session?.access_token ?? null;
    },
    async refreshAccessToken() {
      const { data, error } = await createClient().auth.refreshSession();
      return error ? null : (data.session?.access_token ?? null);
    },
  });
  return browserApiClient;
}
