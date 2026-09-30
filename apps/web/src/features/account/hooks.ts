"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getApiClient } from "@/lib/api/browser";

import { type CurrentUser, fetchCurrentUser, markTourSeen } from "./api";

export const accountKeys = {
  me: ["account", "me"] as const,
};

export function useCurrentUser() {
  return useQuery({
    queryKey: accountKeys.me,
    queryFn: ({ signal }) => fetchCurrentUser(getApiClient(), signal),
  });
}

/**
 * Remember that this person has been shown how the product works.
 *
 * Kept on the account rather than in this browser, so somebody who signed up on a laptop is not
 * shown the walkthrough again on their phone.
 */
export function useMarkTourSeen() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => markTourSeen(getApiClient()),
    onSuccess: (user: CurrentUser) => queryClient.setQueryData(accountKeys.me, user),
  });
}
