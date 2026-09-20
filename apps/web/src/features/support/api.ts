import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";

export const supportStatusSchema = z.enum(["new", "done"]);
export type SupportStatus = z.infer<typeof supportStatusSchema>;

export const feedbackSchema = z.object({
  id: z.uuid(),
  email: z.string().nullable(),
  message: z.string(),
  page: z.string().nullable(),
  status: supportStatusSchema,
  created_at: z.iso.datetime({ offset: true }),
  handled_at: z.iso.datetime({ offset: true }).nullable(),
});

export const templateRequestSchema = z.object({
  id: z.uuid(),
  email: z.string().nullable(),
  note: z.string().nullable(),
  filename: z.string(),
  content_type: z.string(),
  size_bytes: z.number().int(),
  status: supportStatusSchema,
  created_at: z.iso.datetime({ offset: true }),
  handled_at: z.iso.datetime({ offset: true }).nullable(),
});

export type Feedback = z.infer<typeof feedbackSchema>;
export type TemplateRequest = z.infer<typeof templateRequestSchema>;

export function sendFeedback(
  api: ApiClient,
  body: { message: string; page?: string | null; email?: string | null },
): Promise<Feedback> {
  return api.request("/api/v1/feedback", { method: "POST", body, schema: feedbackSchema });
}

/** Sends a template someone already has, for the team to build in by hand. */
export function sendTemplateRequest(
  api: ApiClient,
  file: File,
  note: string,
): Promise<TemplateRequest> {
  const form = new FormData();
  form.append("file", file, file.name);
  if (note.trim()) form.append("note", note.trim());
  return api.upload("/api/v1/template-requests", form, { schema: templateRequestSchema });
}

const countSchema = z.object({ label: z.string(), count: z.number().int() });

export const adminStatsSchema = z.object({
  generated_at: z.iso.datetime({ offset: true }),
  users_total: z.number().int(),
  users_last_7_days: z.number().int(),
  users_last_30_days: z.number().int(),
  records_ready_for_a_resume: z.number().int(),
  resumes_total: z.number().int(),
  letters_total: z.number().int(),
  drafts_total: z.number().int(),
  drafts_last_7_days: z.number().int(),
  interviews_started: z.number().int(),
  interviews_completed: z.number().int(),
  documents_imported: z.number().int(),
  jobs_saved: z.number().int(),
  wrote_a_draft_last_7_days: z.number().int(),
  used_the_assistant_last_7_days: z.number().int(),
  feedback_new: z.number().int(),
  template_requests_new: z.number().int(),
  templates_in_use: z.array(countSchema),
  signups_by_day: z.array(countSchema),
});

export const adminUserSchema = z.object({
  id: z.uuid(),
  email: z.string().nullable(),
  name: z.string().nullable(),
  auth_provider: z.string(),
  created_at: z.iso.datetime({ offset: true }),
  resumes: z.number().int(),
  drafts: z.number().int(),
  interviews: z.number().int(),
  record_ready: z.boolean(),
});

export type AdminStats = z.infer<typeof adminStatsSchema>;
export type AdminUser = z.infer<typeof adminUserSchema>;

export function getAdminStats(api: ApiClient, signal?: AbortSignal): Promise<AdminStats> {
  return api.request("/api/v1/admin/stats", { schema: adminStatsSchema, signal });
}

export function listAdminUsers(api: ApiClient, signal?: AbortSignal): Promise<AdminUser[]> {
  return api.request("/api/v1/admin/users", { schema: z.array(adminUserSchema), signal });
}

export function listAdminFeedback(api: ApiClient, signal?: AbortSignal): Promise<Feedback[]> {
  return api.request("/api/v1/admin/feedback", { schema: z.array(feedbackSchema), signal });
}

export function listAdminTemplateRequests(
  api: ApiClient,
  signal?: AbortSignal,
): Promise<TemplateRequest[]> {
  return api.request("/api/v1/admin/template-requests", {
    schema: z.array(templateRequestSchema),
    signal,
  });
}

export function markFeedback(api: ApiClient, id: string, status: SupportStatus): Promise<Feedback> {
  return api.request(`/api/v1/admin/feedback/${id}`, {
    method: "PATCH",
    body: { status },
    schema: feedbackSchema,
  });
}

export function markTemplateRequest(
  api: ApiClient,
  id: string,
  status: SupportStatus,
): Promise<TemplateRequest> {
  return api.request(`/api/v1/admin/template-requests/${id}`, {
    method: "PATCH",
    body: { status },
    schema: templateRequestSchema,
  });
}

/** Downloads a sent-in template through a temporary link; it never touches disk until saved. */
export async function downloadTemplateRequest(
  api: ApiClient,
  request: TemplateRequest,
): Promise<void> {
  const response = await api.raw(`/api/v1/admin/template-requests/${request.id}/file`);
  const url = URL.createObjectURL(await response.blob());
  try {
    const link = document.createElement("a");
    link.href = url;
    link.download = request.filename;
    link.click();
  } finally {
    URL.revokeObjectURL(url);
  }
}
