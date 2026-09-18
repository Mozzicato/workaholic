import type { Metadata } from "next";

import { AssistantView } from "@/features/interview/components/assistant-view";

export const metadata: Metadata = { title: "Assistant" };

export default function AssistantPage() {
  return <AssistantView />;
}
