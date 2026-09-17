"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getApiClient } from "@/lib/api/browser";

import { createResume, deleteResume, getResume, listResumes, updateResume } from "./api";

export const resumeKeys = {
  all: ["resumes"] as const,
  detail: (id: string) => ["resumes", id] as const,
};

export function useResumes() {
  return useQuery({
    queryKey: resumeKeys.all,
    queryFn: ({ signal }) => listResumes(getApiClient(), signal),
  });
}

export function useResume(id: string) {
  return useQuery({
    queryKey: resumeKeys.detail(id),
    queryFn: ({ signal }) => getResume(getApiClient(), id, signal),
  });
}

export function useCreateResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string; target_role?: string | null }) =>
      createResume(getApiClient(), body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: resumeKeys.all }),
  });
}

export function useUpdateResume(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { title?: string; target_role?: string | null }) =>
      updateResume(getApiClient(), id, body),
    onSuccess: (resume) => {
      queryClient.setQueryData(resumeKeys.detail(id), resume);
      void queryClient.invalidateQueries({ queryKey: resumeKeys.all });
    },
  });
}

export function useDeleteResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteResume(getApiClient(), id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: resumeKeys.all }),
  });
}
