"use client";

import { LoadFailure } from "@/components/feedback/load-failure";
import { Skeleton } from "@/components/ui/skeleton";
import { useProfile } from "@/features/profile/hooks";

import { BasicsForm } from "./basics-form";
import { EducationSection } from "./education-section";
import { ExperienceSection } from "./experience-section";
import { ImportSection } from "./import-section";
import { ProjectsSection } from "./projects-section";
import { SkillsSection } from "./skills-section";

export function ProfileView() {
  const profile = useProfile();

  if (profile.isPending) return <ProfileSkeleton />;
  if (profile.error) {
    return (
      <LoadFailure
        error={profile.error}
        onRetry={() => void profile.refetch()}
        retrying={profile.isRefetching}
        title="We couldn't load your career record"
      />
    );
  }

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">Your career record</h1>
        <p className="max-w-prose leading-relaxed text-muted-foreground">
          Everything a resume can say has to come from here first. Add what you&apos;ve actually
          done — nothing is filled in on your behalf.
        </p>
      </header>

      <ImportSection />
      <BasicsForm basics={profile.data.basics} />
      <EducationSection education={profile.data.education} />
      <ExperienceSection experience={profile.data.experience} />
      <ProjectsSection projects={profile.data.projects} />
      <SkillsSection skills={profile.data.skills} />
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Loading your career record">
      <Skeleton className="h-12 w-72" />
      <Skeleton className="h-64 rounded-xl" />
      <Skeleton className="h-48 rounded-xl" />
    </div>
  );
}
