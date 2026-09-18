"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: routes.dashboard, label: "Resumes" },
  { href: routes.jobs, label: "Jobs" },
  { href: routes.profile, label: "Profile" },
  { href: routes.learn, label: "Learn" },
];

export function MainNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Main" className="flex items-center gap-1">
      {LINKS.map((link) => {
        // The dashboard owns /resumes/* too, so highlight it for those pages.
        const current =
          pathname === link.href ||
          pathname.startsWith(`${link.href}/`) ||
          (link.href === routes.dashboard && pathname.startsWith("/resumes"));
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={current ? "page" : undefined}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm transition-colors",
              current
                ? "bg-accent font-medium text-accent-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
