import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";

export const resumeSchema = z.object({
  id: z.uuid(),
  title: z.string(),
  target_role: z.string().nullable(),
  document_type: z.enum(["resume", "cv"]),
  status: z.enum(["draft", "generating", "ready", "failed"]),
  current_version_id: z.uuid().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});

export type Resume = z.infer<typeof resumeSchema>;

const resumeListSchema = z.array(resumeSchema);

export function listResumes(api: ApiClient, signal?: AbortSignal): Promise<Resume[]> {
  return api.request("/api/v1/resumes", { schema: resumeListSchema, signal });
}

export function getResume(api: ApiClient, id: string, signal?: AbortSignal): Promise<Resume> {
  return api.request(`/api/v1/resumes/${id}`, { schema: resumeSchema, signal });
}

export function createResume(
  api: ApiClient,
  body: { title: string; target_role?: string | null },
): Promise<Resume> {
  return api.request("/api/v1/resumes", {
    method: "POST",
    body,
    schema: resumeSchema,
  });
}

export function updateResume(
  api: ApiClient,
  id: string,
  body: { title?: string; target_role?: string | null },
): Promise<Resume> {
  return api.request(`/api/v1/resumes/${id}`, {
    method: "PATCH",
    body,
    schema: resumeSchema,
  });
}

export function deleteResume(api: ApiClient, id: string): Promise<null> {
  return api.request(`/api/v1/resumes/${id}`, {
    method: "DELETE",
    schema: z.null(),
  });
}
