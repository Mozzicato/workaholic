import type { Metadata } from "next";

import { InterviewView } from "@/features/interview/components/interview-view";

export const metadata: Metadata = { title: "Interview" };

export default async function InterviewPage({ params }: PageProps<"/resumes/[id]/interview">) {
  const { id } = await params;
  return <InterviewView resumeId={id} />;
}
