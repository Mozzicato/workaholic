import Link from "next/link";

import { Logo } from "@/components/brand/logo";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col px-4 py-6 sm:px-6">
      <Logo />
      <div className="m-auto max-w-md py-16 text-center">
        <p className="font-mono text-xs tracking-[0.14em] text-muted-foreground uppercase">404</p>
        <h1 className="mt-3 font-heading text-5xl tracking-tight">This page doesn&apos;t exist.</h1>
        <p className="mt-3 text-muted-foreground">
          The link may be broken, or the page may have moved.
        </p>
        <Link href="/" className={buttonVariants({ size: "lg", className: "mt-8 h-10 px-4" })}>
          Go to the home page
        </Link>
      </div>
    </div>
  );
}
