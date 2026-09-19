import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";

/** Mirrors ResumeTemplate in apps/api/app/models/candidate.py. */
export const resumeTemplateSchema = z.enum([
  "standard",
  "compact",
  "academic",
  "classic",
  "harvard",
  "engineering",
  "modern",
  "bold",
  "sidebar",
  "executive",
  "minimal",
]);
export type ResumeTemplate = z.infer<typeof resumeTemplateSchema>;

export const resumeSchema = z.object({
  id: z.uuid(),
  title: z.string(),
  target_role: z.string().nullable(),
  document_type: z.enum(["resume", "cv", "cover_letter"]),
  template: resumeTemplateSchema,
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

export type DocumentType = Resume["document_type"];

export function createResume(
  api: ApiClient,
  body: {
    title: string;
    target_role?: string | null;
    document_type?: DocumentType;
    template?: ResumeTemplate;
  },
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
  body: { title?: string; target_role?: string | null; template?: ResumeTemplate },
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

/** Who a cover letter is for. Ignored for a resume, required for a letter. */
export type LetterBrief = {
  company: string;
  role?: string | null;
  hiring_manager?: string | null;
  job_advert?: string | null;
};

/** Writes a draft in the resume's own template. */
export function generateVersion(
  api: ApiClient,
  resumeId: string,
  brief?: LetterBrief,
): Promise<ResumeVersion> {
  return api.request(`/api/v1/resumes/${resumeId}/versions`, {
    method: "POST",
    body: brief ? { brief } : {},
    schema: versionSchema,
  });
}

/**
 * A template only changes how a version looks, so any version can be shown in any of them.
 * The API renders it on request; nothing is rewritten.
 */
function withTemplate(path: string, template?: ResumeTemplate): string {
  return template ? `${path}?template=${template}` : path;
}

export function previewUrl(resumeId: string, versionId: string, template?: ResumeTemplate): string {
  return withTemplate(`/api/v1/resumes/${resumeId}/versions/${versionId}/preview`, template);
}

export function pdfUrl(resumeId: string, versionId: string, template?: ResumeTemplate): string {
  return withTemplate(`/api/v1/resumes/${resumeId}/versions/${versionId}/pdf`, template);
}

export async function fetchPreviewHtml(
  api: ApiClient,
  resumeId: string,
  versionId: string,
  template?: ResumeTemplate,
  signal?: AbortSignal,
): Promise<string> {
  const response = await api.raw(previewUrl(resumeId, versionId, template), { signal });
  return response.text();
}

/** The PDF, as a blob plus the filename the API chose for it. */
export async function fetchPdf(
  api: ApiClient,
  resumeId: string,
  versionId: string,
  template?: ResumeTemplate,
): Promise<{ blob: Blob; filename: string }> {
  const response = await api.raw(pdfUrl(resumeId, versionId, template));
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(disposition);
  return { blob: await response.blob(), filename: match?.[1] ?? "resume.pdf" };
}

export const changeSummarySchema = z.object({
  changed: z.array(z.string()),
  unchanged: z.array(z.string()),
  missing_requirements: z.array(z.string()),
});

export const tailoredSchema = z.object({
  version: versionSchema,
  summary: changeSummarySchema,
});

export const atsReportSchema = z.object({
  score: z.number().int(),
  maximum: z.number().int(),
  categories: z.array(
    z.object({
      category: z.string(),
      score: z.number().int(),
      maximum: z.number().int(),
      explanation: z.string(),
    }),
  ),
  checks: z.array(
    z.object({ category: z.string(), name: z.string(), passed: z.boolean(), detail: z.string() }),
  ),
  caveat: z.string(),
});

export type ChangeSummary = z.infer<typeof changeSummarySchema>;
export type Tailored = z.infer<typeof tailoredSchema>;
export type AtsReport = z.infer<typeof atsReportSchema>;

/** A reordered copy of a version, led by what the job asks about. Nothing is reworded. */
export function tailorVersion(
  api: ApiClient,
  resumeId: string,
  versionId: string,
  jobId: string,
): Promise<Tailored> {
  return api.request(`/api/v1/resumes/${resumeId}/versions/${versionId}/tailored`, {
    method: "POST",
    body: { job_id: jobId },
    schema: tailoredSchema,
  });
}

export function getAtsReport(
  api: ApiClient,
  resumeId: string,
  versionId: string,
  jobId: string | null,
  template?: ResumeTemplate,
  signal?: AbortSignal,
): Promise<AtsReport> {
  // Checked in the template being looked at: layout is exactly what an ATS can trip over.
  const params = new URLSearchParams();
  if (jobId) params.set("job_id", jobId);
  if (template) params.set("template", template);
  const query = params.size > 0 ? `?${params.toString()}` : "";
  return api.request(`/api/v1/resumes/${resumeId}/versions/${versionId}/ats${query}`, {
    schema: atsReportSchema,
    signal,
  });
}
