"use client";

import { Button } from "@/components/ui/button";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div role="alert" className="m-auto max-w-md px-4 py-24 text-center">
      <h1 className="font-heading text-4xl tracking-tight">Something went wrong.</h1>
      <p className="mt-3 text-muted-foreground">
        Your information is safe. Please try again — if it keeps happening, come back in a few
        minutes.
      </p>
      <Button className="mt-8 h-10 px-4" size="lg" onClick={reset}>
        Try again
      </Button>
      {error.digest ? (
        <p className="mt-4 font-mono text-[11px] text-muted-foreground">Reference: {error.digest}</p>
      ) : null}
    </div>
  );
}
