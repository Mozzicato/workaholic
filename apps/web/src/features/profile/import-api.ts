import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";

const roleSchema = z.object({
  employer: z.string(),
  title: z.string(),
  start_date: z.string(),
  end_date: z.string(),
  bullets: z.array(z.string()),
  technologies: z.array(z.string()),
});

const projectSchema = z.object({
  name: z.string(),
  description: z.string(),
  technologies: z.array(z.string()),
});

const educationSchema = z.object({
  institution: z.string(),
  qualification: z.string(),
  field_of_study: z.string(),
  start_date: z.string(),
  end_date: z.string(),
});

export const importContentsSchema = z.object({
  full_name: z.string(),
  email: z.string(),
  phone: z.string(),
  location: z.string(),
  headline: z.string(),
  summary: z.string(),
  roles: z.array(roleSchema),
  projects: z.array(projectSchema),
  education: z.array(educationSchema),
  skills: z.array(z.string()),
});

export const importProposalSchema = z.object({
  kind: z.string(),
  pages: z.number().int(),
  contents: importContentsSchema,
  dropped: z.array(z.string()),
  prompt_version: z.string(),
  model: z.string(),
});

export const acceptResultSchema = z.object({
  added: z.array(z.string()),
  skipped: z.array(z.string()),
});

export type ImportContents = z.infer<typeof importContentsSchema>;
export type ImportProposal = z.infer<typeof importProposalSchema>;
export type AcceptResult = z.infer<typeof acceptResultSchema>;

/** Reads an existing resume and proposes what it says. Nothing is recorded yet. */
export function importDocument(api: ApiClient, file: File): Promise<ImportProposal> {
  const form = new FormData();
  form.append("document", file, file.name);
  return api.upload("/api/v1/documents/import", form, { schema: importProposalSchema });
}

/** Adds the confirmed parts of a proposal to the record, as evidence from the document. */
export function acceptImport(api: ApiClient, contents: ImportContents): Promise<AcceptResult> {
  return api.request("/api/v1/documents/import/accept", {
    method: "POST",
    body: contents,
    schema: acceptResultSchema,
  });
}
