import { z } from "zod";

/*
 * Public, browser-safe configuration only. Secrets never belong here: anything prefixed
 * NEXT_PUBLIC_ is inlined into the JavaScript bundle that every visitor downloads.
 */
const publicEnvSchema = z.object({
  NEXT_PUBLIC_SUPABASE_URL: z.url(),
  NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: z
    .string()
    .startsWith("sb_publishable_", "Use the Supabase publishable key, never a secret key"),
  NEXT_PUBLIC_API_URL: z.url(),
  NEXT_PUBLIC_AUTH_GOOGLE_ENABLED: z
    .enum(["true", "false"])
    .optional()
    .transform((value) => value === "true"),
});

// Each variable is referenced by its full name so Next.js can inline it at build time.
export const env = publicEnvSchema.parse({
  NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
  NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_AUTH_GOOGLE_ENABLED: process.env.NEXT_PUBLIC_AUTH_GOOGLE_ENABLED,
});
