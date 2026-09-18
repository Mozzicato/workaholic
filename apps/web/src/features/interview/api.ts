import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";

export const messageSchema = z.object({
  id: z.uuid(),
  sequence: z.number().int(),
  role: z.enum(["agent", "user"]),
  content: z.string(),
  created_at: z.iso.datetime({ offset: true }),
});

export const sessionSchema = z.object({
  id: z.uuid(),
  resume_id: z.uuid().nullable(),
  target_role: z.string().nullable(),
  status: z.enum(["active", "completed", "abandoned"]),
  questions_asked: z.number().int(),
  completed_at: z.iso.datetime({ offset: true }).nullable(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});

export const transcriptSchema = z.object({
  session: sessionSchema,
  messages: z.array(messageSchema),
});

export const turnSchema = z.object({
  session: sessionSchema,
  reply: messageSchema,
  recorded: z.array(z.string()),
  dropped: z.array(z.string()),
  completed: z.boolean(),
});

export type InterviewMessage = z.infer<typeof messageSchema>;
export type InterviewSession = z.infer<typeof sessionSchema>;
export type Transcript = z.infer<typeof transcriptSchema>;
export type Turn = z.infer<typeof turnSchema>;

export function startInterview(
  api: ApiClient,
  body: { resume_id?: string | null; target_role?: string | null },
): Promise<Transcript> {
  return api.request("/api/v1/interviews", { method: "POST", body, schema: transcriptSchema });
}

export function listInterviews(api: ApiClient, signal?: AbortSignal): Promise<InterviewSession[]> {
  return api.request("/api/v1/interviews", { schema: z.array(sessionSchema), signal });
}

export function getInterview(
  api: ApiClient,
  interviewId: string,
  signal?: AbortSignal,
): Promise<Transcript> {
  return api.request(`/api/v1/interviews/${interviewId}`, { schema: transcriptSchema, signal });
}

export function sendAnswer(api: ApiClient, interviewId: string, text: string): Promise<Turn> {
  return api.request(`/api/v1/interviews/${interviewId}/answers`, {
    method: "POST",
    body: { text },
    schema: turnSchema,
  });
}

/** After a document was imported mid-conversation: the next question, from the record as it is now. */
export function continueInterview(api: ApiClient, interviewId: string): Promise<Turn> {
  return api.request(`/api/v1/interviews/${interviewId}/continue`, {
    method: "POST",
    schema: turnSchema,
  });
}

export function abandonInterview(api: ApiClient, interviewId: string): Promise<InterviewSession> {
  return api.request(`/api/v1/interviews/${interviewId}/abandon`, {
    method: "POST",
    schema: sessionSchema,
  });
}

export const transcriptionSchema = z.object({ text: z.string() });

/** Sends one recording and gets back what was heard. The audio is not stored anywhere. */
export async function transcribe(
  api: ApiClient,
  interviewId: string,
  recording: Blob,
): Promise<string> {
  const form = new FormData();
  // The extension matters to the API only as a hint; the content type is what it checks.
  const extension = recording.type.includes("mp4") ? "m4a" : "webm";
  form.append("audio", recording, `answer.${extension}`);
  const { text } = await api.upload(`/api/v1/interviews/${interviewId}/transcriptions`, form, {
    schema: transcriptionSchema,
  });
  return text;
}
