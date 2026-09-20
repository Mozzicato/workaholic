"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getApiClient } from "@/lib/api/browser";

import {
  getAdminStats,
  listAdminFeedback,
  listAdminTemplateRequests,
  listAdminUsers,
  markFeedback,
  markTemplateRequest,
  sendFeedback,
  sendTemplateRequest,
  type SupportStatus,
} from "./api";

export const supportKeys = {
  stats: ["admin", "stats"] as const,
  users: ["admin", "users"] as const,
  feedback: ["admin", "feedback"] as const,
  templateRequests: ["admin", "template-requests"] as const,
};

export function useSendFeedback() {
  return useMutation({
    mutationFn: (body: { message: string; page?: string | null; email?: string | null }) =>
      sendFeedback(getApiClient(), body),
  });
}

export function useSendTemplateRequest() {
  return useMutation({
    mutationFn: ({ file, note }: { file: File; note: string }) =>
      sendTemplateRequest(getApiClient(), file, note),
  });
}

export function useAdminStats() {
  return useQuery({
    queryKey: supportKeys.stats,
    queryFn: ({ signal }) => getAdminStats(getApiClient(), signal),
  });
}

export function useAdminUsers() {
  return useQuery({
    queryKey: supportKeys.users,
    queryFn: ({ signal }) => listAdminUsers(getApiClient(), signal),
  });
}

export function useAdminFeedback() {
  return useQuery({
    queryKey: supportKeys.feedback,
    queryFn: ({ signal }) => listAdminFeedback(getApiClient(), signal),
  });
}

export function useAdminTemplateRequests() {
  return useQuery({
    queryKey: supportKeys.templateRequests,
    queryFn: ({ signal }) => listAdminTemplateRequests(getApiClient(), signal),
  });
}

export function useMarkFeedback() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: SupportStatus }) =>
      markFeedback(getApiClient(), id, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: supportKeys.feedback });
      void queryClient.invalidateQueries({ queryKey: supportKeys.stats });
    },
  });
}

export function useMarkTemplateRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: SupportStatus }) =>
      markTemplateRequest(getApiClient(), id, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: supportKeys.templateRequests });
      void queryClient.invalidateQueries({ queryKey: supportKeys.stats });
    },
  });
}
