import { QueryCache, QueryClient } from "@tanstack/react-query";

import { ApiError } from "@/lib/api/errors";
import { loginPathFor } from "@/lib/routes";

function shouldRetry(failureCount: number, error: unknown): boolean {
  // Client errors (bad input, not found, signed out) won't fix themselves on retry.
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
  return failureCount < 2;
}

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError(error) {
        // The session is gone even after a refresh attempt: send the user back to sign in.
        if (error instanceof ApiError && error.isAuthError && typeof window !== "undefined") {
          const here = `${window.location.pathname}${window.location.search}`;
          window.location.assign(loginPathFor(here));
        }
      },
    }),
    defaultOptions: {
      queries: { staleTime: 30_000, retry: shouldRetry },
      mutations: { retry: false },
    },
  });
}
