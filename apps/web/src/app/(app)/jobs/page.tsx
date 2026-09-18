import type { Metadata } from "next";

import { JobsView } from "@/features/jobs/components/jobs-view";

export const metadata: Metadata = { title: "Jobs" };

export default function JobsPage() {
  return <JobsView />;
}
