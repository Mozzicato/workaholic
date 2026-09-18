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

export const resumeTemplateSchema = z.enum(["standard", "compact", "academic"]);
export type ResumeTemplate = z.infer<typeof resumeTemplateSchema>;

export const versionSummarySchema = z.object({
  id: z.uuid(),
  resume_id: z.uuid(),
  version_number: z.number().int(),
  label: z.string(),
  template: resumeTemplateSchema,
  created_at: z.iso.datetime({ offset: true }),
});

/** The document itself is rendered by the API; the app needs only enough of it to describe one. */
export const versionSchema = versionSummarySchema.extend({
  schema_version: z.string(),
  prompt_version: z.string(),
  model: z.string().nullable(),
  content: z.looseObject({
    summary: z.string().nullable().optional(),
    experience: z.array(z.unknown()).default([]),
    projects: z.array(z.unknown()).default([]),
    education: z.array(z.unknown()).default([]),
  }),
});

export type ResumeVersionSummary = z.infer<typeof versionSummarySchema>;
export type ResumeVersion = z.infer<typeof versionSchema>;

export function listVersions(
  api: ApiClient,
  resumeId: string,
  signal?: AbortSignal,
): Promise<ResumeVersionSummary[]> {
  return api.request(`/api/v1/resumes/${resumeId}/versions`, {
    schema: z.array(versionSummarySchema),
    signal,
  });
}

export function generateVersion(
  api: ApiClient,
  resumeId: string,
  template: ResumeTemplate,
): Promise<ResumeVersion> {
  return api.request(`/api/v1/resumes/${resumeId}/versions`, {
    method: "POST",
    body: { template },
    schema: versionSchema,
  });
}

export function previewUrl(resumeId: string, versionId: string): string {
  return `/api/v1/resumes/${resumeId}/versions/${versionId}/preview`;
}

export function pdfUrl(resumeId: string, versionId: string): string {
  return `/api/v1/resumes/${resumeId}/versions/${versionId}/pdf`;
}

export async function fetchPreviewHtml(
  api: ApiClient,
  resumeId: string,
  versionId: string,
  signal?: AbortSignal,
): Promise<string> {
  const response = await api.raw(previewUrl(resumeId, versionId), { signal });
  return response.text();
}

/** The PDF, as a blob plus the filename the API chose for it. */
export async function fetchPdf(
  api: ApiClient,
  resumeId: string,
  versionId: string,
): Promise<{ blob: Blob; filename: string }> {
  const response = await api.raw(pdfUrl(resumeId, versionId));
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(disposition);
  return { blob: await response.blob(), filename: match?.[1] ?? "resume.pdf" };
}
