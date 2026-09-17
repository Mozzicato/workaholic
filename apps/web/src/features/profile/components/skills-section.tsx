"use client";

import { PlusIcon, XIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import type { Skill } from "@/features/profile/api";
import { useUpdateProfile } from "@/features/profile/hooks";
import { orNull } from "@/features/profile/lines";
import { errorMessage } from "@/lib/api/errors";

import { EmptySectionNote, SectionCard } from "./section-card";

export function SkillsSection({ skills }: { skills: Skill[] }) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [error, setError] = useState<string | null>(null);
  const updateProfile = useUpdateProfile();

  async function save(next: Skill[], success: string) {
    try {
      await updateProfile.mutateAsync({ skills: next });
      toast.success(success);
      return true;
    } catch (failure) {
      setError(errorMessage(failure));
      return false;
    }
  }

  async function onAdd(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Enter a skill first.");
      return;
    }
    if (skills.some((skill) => skill.name.toLowerCase() === trimmed.toLowerCase())) {
      setError(`${trimmed} is already on your list.`);
      return;
    }
    const added = await save(
      [...skills, { name: trimmed, category: orNull(category) }],
      `${trimmed} added`,
    );
    if (added) {
      setName("");
      setCategory("");
    }
  }

  async function onRemove(skill: Skill) {
    setError(null);
    await save(
      skills.filter((candidate) => candidate !== skill),
      `${skill.name} removed`,
    );
  }

  return (
    <SectionCard
      id="skills"
      title="Skills"
      description="Only what you can actually back up in an interview. Each one has to be earned somewhere in your experience."
    >
      <div className="space-y-5">
        {skills.length === 0 ? (
          <EmptySectionNote>No skills yet.</EmptySectionNote>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {skills.map((skill, index) => (
              <li
                key={skill.id ?? `${skill.name}-${index}`}
                className="flex items-center gap-1.5 rounded-full border bg-background py-1 pr-1 pl-3 text-sm"
              >
                <span>{skill.name}</span>
                {skill.category ? (
                  <span className="text-muted-foreground">· {skill.category}</span>
                ) : null}
                <button
                  type="button"
                  onClick={() => void onRemove(skill)}
                  disabled={updateProfile.isPending}
                  aria-label={`Remove ${skill.name}`}
                  className="flex size-5 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none disabled:opacity-50"
                >
                  <XIcon className="size-3.5" aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        )}

        <form onSubmit={onAdd} noValidate className="flex flex-wrap items-end gap-3">
          <Field className="w-full min-w-40 flex-1 sm:w-auto">
            <FieldLabel htmlFor="skill_name">Skill</FieldLabel>
            <Input
              id="skill_name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="PostgreSQL"
              maxLength={120}
            />
          </Field>
          <Field className="w-full min-w-40 flex-1 sm:w-auto">
            <FieldLabel htmlFor="skill_category">Group (optional)</FieldLabel>
            <Input
              id="skill_category"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              placeholder="Databases"
              maxLength={120}
            />
          </Field>
          <Button type="submit" variant="outline" disabled={updateProfile.isPending}>
            {updateProfile.isPending ? <Spinner /> : <PlusIcon aria-hidden="true" />}
            Add
          </Button>
        </form>

        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
      </div>
    </SectionCard>
  );
}
