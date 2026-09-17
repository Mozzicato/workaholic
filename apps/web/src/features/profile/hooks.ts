"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getApiClient } from "@/lib/api/browser";

import { getProfile, updateProfile, type ProfileUpdate } from "./api";

export const profileKeys = { profile: ["profile"] as const };

export function useProfile() {
  return useQuery({
    queryKey: profileKeys.profile,
    queryFn: ({ signal }) => getProfile(getApiClient(), signal),
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (update: ProfileUpdate) => updateProfile(getApiClient(), update),
    onSuccess: (profile) => queryClient.setQueryData(profileKeys.profile, profile),
  });
}
