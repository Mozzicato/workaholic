"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { PencilIcon, PlusIcon, Trash2Icon } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { FormErrorAlert } from "@/features/auth/components/form-alert";
import type { Project } from "@/features/profile/api";
import { checkDateOrder, monthField } from "@/features/profile/form";
import { useUpdateProfile } from "@/features/profile/hooks";
import {
  formatRange,
  fromCommas,
  fromLines,
  orNull,
  toCommas,
  toLines,
} from "@/features/profile/lines";
import { errorMessage } from "@/lib/api/errors";

import { EmptySectionNote, SectionCard } from "./section-card";

const schema = z
  .object({
    name: z
      .string()
      .trim()
      .min(1, "Give the project a name")
      .max(120, "Use 120 characters or fewer"),
    description: z.string().trim().max(2000, "Use 2000 characters or fewer"),
    url: z.union([z.literal(""), z.url("Enter a full link, starting with https://")]),
    start_date: monthField,
    end_date: monthField,
    outcomes: z.string(),
    technologies: z.string(),
  })
  .superRefine(checkDateOrder);

type Values = z.infer<typeof schema>;

const BLANK: Values = {
  name: "",
  description: "",
  url: "",
  start_date: "",
  end_date: "",
  outcomes: "",
  technologies: "",
};

export function ProjectsSection({ projects }: { projects: Project[] }) {
  const [editing, setEditing] = useState<{
    item: Project;
    index: number;
  } | null>(null);
  const [adding, setAdding] = useState(false);
  const updateProfile = useUpdateProfile();

  async function save(next: Project[], success: string) {
    await updateProfile.mutateAsync({ projects: next });
    toast.success(success);
  }

  async function onRemove(index: number) {
    try {
      await save(
        projects.filter((_, position) => position !== index),
        "Project removed",
      );
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  return (
    <SectionCard
      id="projects"
      title="Projects"
      description="Things you built or shipped outside a job — coursework, side projects, open source."
      action={
        projects.length > 0 ? (
          <Button variant="outline" size="sm" onClick={() => setAdding(true)}>
            <PlusIcon aria-hidden="true" />
            Add project
          </Button>
        ) : null
      }
    >
      {projects.length === 0 ? (
        <div className="space-y-4">
          <EmptySectionNote>No projects yet.</EmptySectionNote>
          <Button variant="outline" onClick={() => setAdding(true)}>
            <PlusIcon aria-hidden="true" />
            Add your first project
          </Button>
        </div>
      ) : (
        <ul className="divide-y">
          {projects.map((item, index) => (
            <li
              key={item.id ?? `${item.name}-${index}`}
              className="flex items-start gap-4 py-4 first:pt-0 last:pb-0"
            >
              <div className="min-w-0 flex-1 space-y-1">
                <p className="font-medium">{item.name}</p>
                {formatRange(item.start_date, item.end_date) ? (
                  <p className="text-sm text-muted-foreground">
                    {formatRange(item.start_date, item.end_date)}
                  </p>
                ) : null}
                {item.description ? (
                  <p className="text-sm leading-relaxed">{item.description}</p>
                ) : null}
                {item.outcomes.length > 0 ? (
                  <ul className="mt-2 space-y-1 text-sm leading-relaxed">
                    {item.outcomes.map((outcome, position) => (
                      <li key={position} className="flex gap-2">
                        <span aria-hidden="true" className="text-muted-foreground">
                          •
                        </span>
                        <span>{outcome}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
                <div className="flex flex-wrap gap-x-3 pt-1 text-sm text-muted-foreground">
                  {item.technologies.length > 0 ? (
                    <span>{item.technologies.join(", ")}</span>
                  ) : null}
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="underline underline-offset-4 hover:text-foreground"
                    >
                      Link
                    </a>
                  ) : null}
                </div>
              </div>
              <div className="flex shrink-0 gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Edit ${item.name}`}
                  onClick={() => setEditing({ item, index })}
                >
                  <PencilIcon aria-hidden="true" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Remove ${item.name}`}
                  disabled={updateProfile.isPending}
                  onClick={() => void onRemove(index)}
                >
                  <Trash2Icon aria-hidden="true" />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <ProjectDialog
        key={editing ? (editing.item.id ?? String(editing.index)) : "new"}
        open={adding || editing !== null}
        item={editing?.item ?? null}
        onClose={() => {
          setAdding(false);
          setEditing(null);
        }}
        onSubmit={async (values) => {
          const entry: Project = {
            ...(editing?.item ?? {}),
            name: values.name,
            description: orNull(values.description),
            url: orNull(values.url),
            start_date: orNull(values.start_date),
            end_date: orNull(values.end_date),
            outcomes: fromLines(values.outcomes),
            technologies: fromCommas(values.technologies),
          };
          if (editing) {
            await save(
              projects.map((current, index) => (index === editing.index ? entry : current)),
              "Project updated",
            );
          } else {
            await save([...projects, entry], "Project added");
          }
        }}
      />
    </SectionCard>
  );
}

function ProjectDialog({
  open,
  item,
  onClose,
  onSubmit,
}: {
  open: boolean;
  item: Project | null;
  onClose: () => void;
  onSubmit: (values: Values) => Promise<void>;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: item
      ? {
          name: item.name,
          description: item.description ?? "",
          url: item.url ?? "",
          start_date: item.start_date ?? "",
          end_date: item.end_date ?? "",
          outcomes: toLines(item.outcomes),
          technologies: toCommas(item.technologies),
        }
      : BLANK,
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setFormError(null);
          onClose();
        }
      }}
    >
      <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="font-heading text-2xl">
            {item ? "Edit project" : "Add a project"}
          </DialogTitle>
          <DialogDescription>
            What it was, what you did, and how it turned out — in your own words.
          </DialogDescription>
        </DialogHeader>

        <form
          noValidate
          className="space-y-5"
          onSubmit={handleSubmit(async (values) => {
            setFormError(null);
            try {
              await onSubmit(values);
              onClose();
            } catch (error) {
              setFormError(errorMessage(error));
            }
          })}
        >
          <FormErrorAlert message={formError} />

          <Field data-invalid={Boolean(errors.name)}>
            <FieldLabel htmlFor="project_name">Name</FieldLabel>
            <Input
              id="project_name"
              placeholder="Campus bus tracker"
              aria-invalid={Boolean(errors.name)}
              {...register("name")}
            />
            <FieldError errors={[errors.name]} />
          </Field>

          <Field data-invalid={Boolean(errors.description)}>
            <FieldLabel htmlFor="project_description">What it is</FieldLabel>
            <Textarea
              id="project_description"
              rows={3}
              aria-invalid={Boolean(errors.description)}
              {...register("description")}
            />
            <FieldError errors={[errors.description]} />
          </Field>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field data-invalid={Boolean(errors.start_date)}>
              <FieldLabel htmlFor="project_start">Started (optional)</FieldLabel>
              <Input
                id="project_start"
                placeholder="2025-01"
                inputMode="numeric"
                aria-invalid={Boolean(errors.start_date)}
                {...register("start_date")}
              />
              {errors.start_date ? (
                <FieldError errors={[errors.start_date]} />
              ) : (
                <FieldDescription>Year, or year and month.</FieldDescription>
              )}
            </Field>
            <Field data-invalid={Boolean(errors.end_date)}>
              <FieldLabel htmlFor="project_end">Finished (optional)</FieldLabel>
              <Input
                id="project_end"
                placeholder="2025-04"
                inputMode="numeric"
                aria-invalid={Boolean(errors.end_date)}
                {...register("end_date")}
              />
              <FieldError errors={[errors.end_date]} />
            </Field>
          </div>

          <Field data-invalid={Boolean(errors.outcomes)}>
            <FieldLabel htmlFor="project_outcomes">What came of it (optional)</FieldLabel>
            <Textarea
              id="project_outcomes"
              rows={3}
              placeholder={"Used by 40 students in the first week\nOpen sourced, 12 stars"}
              aria-invalid={Boolean(errors.outcomes)}
              {...register("outcomes")}
            />
            <FieldDescription>One per line.</FieldDescription>
          </Field>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field data-invalid={Boolean(errors.url)}>
              <FieldLabel htmlFor="project_url">Link (optional)</FieldLabel>
              <Input
                id="project_url"
                placeholder="https://github.com/you/project"
                aria-invalid={Boolean(errors.url)}
                {...register("url")}
              />
              <FieldError errors={[errors.url]} />
            </Field>
            <Field>
              <FieldLabel htmlFor="project_tech">Tools used (optional)</FieldLabel>
              <Input
                id="project_tech"
                placeholder="TypeScript, Next.js"
                {...register("technologies")}
              />
              <FieldDescription>Separated by commas.</FieldDescription>
            </Field>
          </div>

          <DialogFooter showCloseButton>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : null}
              {isSubmitting ? "Saving…" : item ? "Save changes" : "Add project"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
