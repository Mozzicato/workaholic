"use client";

import { RotateCwIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError, errorMessage } from "@/lib/api/errors";

/** Shown when a page's data could not be loaded. Offers a retry rather than a dead end. */
export function LoadFailure({
  error,
  onRetry,
  retrying,
  title,
}: {
  error: unknown;
  onRetry: () => void;
  retrying: boolean;
  title: string;
}) {
  return (
    <div role="alert" className="mx-auto max-w-md rounded-xl border bg-card p-8 text-center">
      <h1 className="font-heading text-3xl">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{errorMessage(error)}</p>
      <Button className="mt-6" variant="outline" onClick={onRetry} disabled={retrying}>
        <RotateCwIcon className={retrying ? "animate-spin" : undefined} aria-hidden="true" />
        Try again
      </Button>
      {error instanceof ApiError && error.requestId ? (
        <p className="mt-4 font-mono text-[11px] text-muted-foreground">
          Reference: {error.requestId}
        </p>
      ) : null}
    </div>
  );
}
