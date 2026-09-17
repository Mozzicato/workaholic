import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";

/** Mirrors the API's candidate profile schema (apps/api/app/schemas/candidate.py). */

const monthPattern = /^\d{4}(-(0[1-9]|1[0-2]))?$/;
const month = z
  .string()
  .regex(monthPattern, "Use a year, or a year and month like 2025-06")
  .nullish();

export const basicsSchema = z.object({
  full_name: z.string().max(120).nullish(),
  headline: z.string().max(200).nullish(),
  email: z.string().max(320).nullish(),
  phone: z.string().max(40).nullish(),
  location: z.string().max(120).nullish(),
  summary: z.string().max(2000).nullish(),
});

export const skillSchema = z.object({
  id: z.string().optional(),
  evidence_ids: z.array(z.string()).optional(),
  name: z.string().min(1).max(120),
  category: z.string().max(120).nullish(),
});

export const experienceSchema = z.object({
  id: z.string().optional(),
  evidence_ids: z.array(z.string()).optional(),
  employer: z.string().min(1).max(120),
  title: z.string().min(1).max(120),
  location: z.string().max(120).nullish(),
  is_current: z.boolean().default(false),
  start_date: month,
  end_date: month,
  bullets: z.array(z.string().min(1).max(500)).max(20).default([]),
  technologies: z.array(z.string().min(1).max(120)).max(40).default([]),
});

export const projectSchema = z.object({
  id: z.string().optional(),
  evidence_ids: z.array(z.string()).optional(),
  name: z.string().min(1).max(120),
  description: z.string().max(2000).nullish(),
  url: z.url().nullish(),
  start_date: month,
  end_date: month,
  technologies: z.array(z.string().min(1).max(120)).max(40).default([]),
  outcomes: z.array(z.string().min(1).max(500)).max(20).default([]),
});

export const profileSchema = z.object({
  id: z.uuid(),
  basics: basicsSchema,
  links: z.object({
    website: z.string().nullish(),
    github: z.string().nullish(),
    linkedin: z.string().nullish(),
    other: z.array(z.object({ label: z.string(), url: z.string() })).default([]),
  }),
  experience: z.array(experienceSchema),
  education: z.array(z.record(z.string(), z.unknown())),
  projects: z.array(projectSchema),
  skills: z.array(skillSchema),
  achievements: z.array(z.record(z.string(), z.unknown())),
  certifications: z.array(z.record(z.string(), z.unknown())),
  languages: z.array(z.record(z.string(), z.unknown())),
  updated_at: z.iso.datetime({ offset: true }),
});

export type CandidateProfile = z.infer<typeof profileSchema>;
export type Basics = z.infer<typeof basicsSchema>;
export type Skill = z.infer<typeof skillSchema>;
export type Experience = z.infer<typeof experienceSchema>;
export type Project = z.infer<typeof projectSchema>;

export type ProfileUpdate = {
  basics?: Basics;
  skills?: Skill[];
  experience?: Experience[];
  projects?: Project[];
};

export function getProfile(api: ApiClient, signal?: AbortSignal): Promise<CandidateProfile> {
  return api.request("/api/v1/profile", { schema: profileSchema, signal });
}

export function updateProfile(api: ApiClient, body: ProfileUpdate): Promise<CandidateProfile> {
  return api.request("/api/v1/profile", {
    method: "PATCH",
    body,
    schema: profileSchema,
  });
}
