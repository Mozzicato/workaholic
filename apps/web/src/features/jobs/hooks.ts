"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { profileKeys } from "@/features/profile/hooks";
import { getApiClient } from "@/lib/api/browser";

import {
  createJob,
  deleteJob,
  getJob,
  getMatch,
  listJobs,
  reanalyseJob,
  type JobCreate,
} from "./api";

export const jobKeys = {
  all: ["jobs"] as const,
  detail: (id: string) => ["jobs", id] as const,
  match: (id: string) => ["jobs", id, "match"] as const,
};

export function useJobs() {
  return useQuery({
    queryKey: jobKeys.all,
    queryFn: ({ signal }) => listJobs(getApiClient(), signal),
  });
}

export function useJob(id: string) {
  return useQuery({
    queryKey: jobKeys.detail(id),
    queryFn: ({ signal }) => getJob(getApiClient(), id, signal),
  });
}

/** Recomputed whenever the record changes, since that is what it measures. */
export function useMatch(id: string) {
  return useQuery({
    queryKey: [...jobKeys.match(id), profileKeys.profile],
    queryFn: ({ signal }) => getMatch(getApiClient(), id, signal),
  });
}

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: JobCreate) => createJob(getApiClient(), body),
    onSuccess: (job) => {
      queryClient.setQueryData(jobKeys.detail(job.id), job);
      void queryClient.invalidateQueries({ queryKey: jobKeys.all });
    },
  });
}

export function useReanalyseJob(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => reanalyseJob(getApiClient(), id),
    onSuccess: (job) => {
      queryClient.setQueryData(jobKeys.detail(id), job);
      void queryClient.invalidateQueries({ queryKey: jobKeys.match(id) });
    },
  });
}

export function useDeleteJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteJob(getApiClient(), id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: jobKeys.all }),
  });
}
