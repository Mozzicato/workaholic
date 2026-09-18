import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";

export const analysisSchema = z.object({
  role: z.string().default(""),
  seniority: z.string().default(""),
  required_skills: z.array(z.string()).default([]),
  preferred_skills: z.array(z.string()).default([]),
  responsibilities: z.array(z.string()).default([]),
  qualifications: z.array(z.string()).default([]),
  keywords: z.array(z.string()).default([]),
  domain_terms: z.array(z.string()).default([]),
  education_requirements: z.array(z.string()).default([]),
  experience_requirements: z.array(z.string()).default([]),
});

export const jobSchema = z.object({
  id: z.uuid(),
  title: z.string(),
  company: z.string().nullable(),
  source_url: z.string().nullable(),
  raw_text: z.string(),
  analysis: analysisSchema,
  analysis_model: z.string().nullable(),
  prompt_version: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});

export const jobSummarySchema = z.object({
  id: z.uuid(),
  title: z.string(),
  company: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});

export const matchSchema = z.object({
  requirement: z.string(),
  state: z.enum(["MATCHED", "PARTIALLY_MATCHED", "NOT_FOUND"]),
  kind: z.string(),
  evidence: z.array(z.string()),
  explanation: z.string(),
});

export const matchReportSchema = z.object({
  job_id: z.uuid(),
  matches: z.array(matchSchema),
  matched: z.number().int(),
  partially_matched: z.number().int(),
  not_found: z.number().int(),
});

export type Job = z.infer<typeof jobSchema>;
export type JobSummary = z.infer<typeof jobSummarySchema>;
export type RequirementMatch = z.infer<typeof matchSchema>;
export type MatchReport = z.infer<typeof matchReportSchema>;

export type JobCreate = {
  title: string;
  company?: string | null;
  source_url?: string | null;
  raw_text: string;
};

export function listJobs(api: ApiClient, signal?: AbortSignal): Promise<JobSummary[]> {
  return api.request("/api/v1/jobs", { schema: z.array(jobSummarySchema), signal });
}

export function getJob(api: ApiClient, id: string, signal?: AbortSignal): Promise<Job> {
  return api.request(`/api/v1/jobs/${id}`, { schema: jobSchema, signal });
}

export function createJob(api: ApiClient, body: JobCreate): Promise<Job> {
  return api.request("/api/v1/jobs", { method: "POST", body, schema: jobSchema });
}

export function reanalyseJob(api: ApiClient, id: string): Promise<Job> {
  return api.request(`/api/v1/jobs/${id}/analysis`, { method: "POST", schema: jobSchema });
}

export function deleteJob(api: ApiClient, id: string): Promise<null> {
  return api.request(`/api/v1/jobs/${id}`, { method: "DELETE", schema: z.null() });
}

export function getMatch(api: ApiClient, id: string, signal?: AbortSignal): Promise<MatchReport> {
  return api.request(`/api/v1/jobs/${id}/match`, { schema: matchReportSchema, signal });
}
