"use client";

import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { makeQueryClient } from "@/lib/query-client";

export function AppProviders({ children }: { children: ReactNode }) {
  // One client per browser tab, created lazily so server renders never share state.
  const [queryClient] = useState<QueryClient>(makeQueryClient);
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
