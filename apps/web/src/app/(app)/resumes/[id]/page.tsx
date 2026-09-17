import type { Metadata } from "next";

import { ResumeDetail } from "@/features/resumes/components/resume-detail";

export const metadata: Metadata = { title: "Resume" };

export default async function ResumePage({ params }: PageProps<"/resumes/[id]">) {
  const { id } = await params;
  return <ResumeDetail id={id} />;
}
