"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { profileKeys } from "@/features/profile/hooks";
import { getApiClient } from "@/lib/api/browser";

import { abandonInterview, getInterview, listInterviews, sendAnswer, startInterview } from "./api";

export const interviewKeys = {
  all: ["interviews"] as const,
  detail: (id: string) => ["interviews", id] as const,
};

export function useInterviews() {
  return useQuery({
    queryKey: interviewKeys.all,
    queryFn: ({ signal }) => listInterviews(getApiClient(), signal),
  });
}

export function useInterview(interviewId: string | null) {
  return useQuery({
    queryKey: interviewKeys.detail(interviewId ?? "none"),
    queryFn: ({ signal }) => getInterview(getApiClient(), interviewId as string, signal),
    enabled: Boolean(interviewId),
  });
}

export function useStartInterview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { resume_id?: string | null; target_role?: string | null }) =>
      startInterview(getApiClient(), body),
    onSuccess: (transcript) => {
      queryClient.setQueryData(interviewKeys.detail(transcript.session.id), transcript);
      void queryClient.invalidateQueries({ queryKey: interviewKeys.all });
    },
  });
}

export function useSendAnswer(interviewId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => sendAnswer(getApiClient(), interviewId, text),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: interviewKeys.detail(interviewId) });
      // The record just grew: anything showing it has to refetch.
      void queryClient.invalidateQueries({ queryKey: profileKeys.profile });
    },
  });
}

export function useAbandonInterview(interviewId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => abandonInterview(getApiClient(), interviewId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: interviewKeys.detail(interviewId) });
      void queryClient.invalidateQueries({ queryKey: interviewKeys.all });
    },
  });
}
