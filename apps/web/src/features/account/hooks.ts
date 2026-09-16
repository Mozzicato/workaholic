"use client";

import { useQuery } from "@tanstack/react-query";

import { getApiClient } from "@/lib/api/browser";

import { fetchCurrentUser } from "./api";

export const accountKeys = {
  me: ["account", "me"] as const,
};

export function useCurrentUser() {
  return useQuery({
    queryKey: accountKeys.me,
    queryFn: ({ signal }) => fetchCurrentUser(getApiClient(), signal),
  });
}
