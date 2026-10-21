import { Logo } from "@/components/brand/logo";
import { WarmApi } from "@/components/system/warm-api";

export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      {/* Somebody about to sign in is about to need the API. Start it now. */}
      <WarmApi />
      <aside className="relative hidden overflow-hidden bg-primary p-12 text-primary-foreground lg:flex lg:flex-col lg:justify-between">
        <Logo tone="inverse" />

        <figure className="max-w-md space-y-6">
          <blockquote className="font-heading text-5xl leading-[1.05] tracking-tight">
            We improve how you say it.
            <br />
            <em className="text-primary-foreground/70">Never what happened.</em>
          </blockquote>
          <figcaption className="max-w-sm text-sm leading-relaxed text-primary-foreground/75">
            Every line Workaholic writes traces back to something you told it. If a stronger claim
            needs a fact we don&apos;t have, we ask you — we don&apos;t make it up.
          </figcaption>
        </figure>

        <p className="text-xs text-primary-foreground/60">
          Your career data is private to your account.
        </p>

        {/* Faint ruled-paper texture */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-[0.07] [background-image:repeating-linear-gradient(to_bottom,transparent_0,transparent_31px,currentColor_31px,currentColor_32px)]"
        />
      </aside>

      <main className="flex flex-col px-5 py-6 sm:px-10">
        <div className="lg:hidden">
          <Logo />
        </div>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
          {children}
        </div>
      </main>
    </div>
  );
}
