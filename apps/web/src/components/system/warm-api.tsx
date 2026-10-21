"use client";

import { useEffect } from "react";

import { env } from "@/lib/env";

/**
 * Wake the API while somebody is still reading the page.
 *
 * The API scales to zero when nobody is using it, which costs nothing but means the first request
 * after a quiet spell waits around fifteen seconds for a container to start. Landing on the sign-in
 * page is the earliest honest signal that a person is about to need it, and they will spend a good
 * few seconds reading and typing — so the container boots during that time instead of during their
 * first real request.
 *
 * It is a nudge, not a dependency: nothing waits on it and a failure is ignored. `/health` touches
 * no database and returns a constant, so this is the cheapest request that still starts a replica.
 */
export function WarmApi() {
  useEffect(() => {
    // Deliberately not aborted on unmount: by then the request has done its job, and cancelling
    // it on a fast navigation would undo the very thing it is here for.
    void fetch(`${env.NEXT_PUBLIC_API_URL}/health`, { cache: "no-store" }).catch(() => {
      // Nothing to do. If the API is unreachable, the page that needs it will say so properly.
    });
  }, []);

  return null;
}
