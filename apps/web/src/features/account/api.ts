import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";

export const currentUserSchema = z.object({
  id: z.uuid(),
  email: z.string().nullable(),
  name: z.string().nullable(),
  auth_provider: z.string(),
  created_at: z.iso.datetime({ offset: true }),
});

export type CurrentUser = z.infer<typeof currentUserSchema>;

export function fetchCurrentUser(api: ApiClient, signal?: AbortSignal): Promise<CurrentUser> {
  return api.request("/api/v1/me", { schema: currentUserSchema, signal });
}
