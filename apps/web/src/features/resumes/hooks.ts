"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getApiClient } from "@/lib/api/browser";

import {
  createResume,
  deleteResume,
  fetchPdf,
  fetchPreviewHtml,
  generateVersion,
  getAtsReport,
  getResume,
  listResumes,
  listVersions,
  tailorVersion,
  updateResume,
  type DocumentType,
  type LetterBrief,
  type ResumeTemplate,
} from "./api";

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
    mutationFn: (body: {
      title: string;
      target_role?: string | null;
      document_type?: DocumentType;
    }) => createResume(getApiClient(), body),
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

export const versionKeys = {
  all: (resumeId: string) => ["resumes", resumeId, "versions"] as const,
  preview: (resumeId: string, versionId: string) =>
    ["resumes", resumeId, "versions", versionId, "preview"] as const,
};

export function useVersions(resumeId: string) {
  return useQuery({
    queryKey: versionKeys.all(resumeId),
    queryFn: ({ signal }) => listVersions(getApiClient(), resumeId, signal),
  });
}

export function usePreviewHtml(resumeId: string, versionId: string | undefined) {
  return useQuery({
    queryKey: versionKeys.preview(resumeId, versionId ?? "none"),
    queryFn: ({ signal }) => fetchPreviewHtml(getApiClient(), resumeId, versionId!, signal),
    enabled: Boolean(versionId),
    staleTime: Infinity, // a version never changes once written
  });
}

export function useGenerateVersion(resumeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ template, brief }: { template: ResumeTemplate; brief?: LetterBrief }) =>
      generateVersion(getApiClient(), resumeId, template, brief),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: versionKeys.all(resumeId) });
      void queryClient.invalidateQueries({ queryKey: resumeKeys.detail(resumeId) });
      void queryClient.invalidateQueries({ queryKey: resumeKeys.all });
    },
  });
}

/** Saves the PDF through a temporary link: the file never leaves the browser's memory. */
export function useDownloadPdf(resumeId: string) {
  return useMutation({
    mutationFn: async (versionId: string) => {
      const { blob, filename } = await fetchPdf(getApiClient(), resumeId, versionId);
      const url = URL.createObjectURL(blob);
      try {
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.click();
      } finally {
        URL.revokeObjectURL(url);
      }
    },
  });
}

export function useTailor(resumeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ versionId, jobId }: { versionId: string; jobId: string }) =>
      tailorVersion(getApiClient(), resumeId, versionId, jobId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: versionKeys.all(resumeId) });
      void queryClient.invalidateQueries({ queryKey: resumeKeys.detail(resumeId) });
    },
  });
}

/** Only fetched on request: it prints a PDF on the server to check its text reads back. */
export function useAtsReport(resumeId: string, versionId: string | null, jobId: string | null) {
  return useQuery({
    queryKey: ["resumes", resumeId, "versions", versionId, "ats", jobId ?? "none"],
    queryFn: ({ signal }) =>
      getAtsReport(getApiClient(), resumeId, versionId as string, jobId, signal),
    enabled: false,
    staleTime: Infinity,
  });
}
