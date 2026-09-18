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
import { FormErrorAlert } from "@/features/auth/components/form-alert";
import type { Education } from "@/features/profile/api";
import { checkDateOrder, monthField } from "@/features/profile/form";
import { useUpdateProfile } from "@/features/profile/hooks";
import { formatRange, orNull } from "@/features/profile/lines";
import { errorMessage } from "@/lib/api/errors";

import { EmptySectionNote, SectionCard } from "./section-card";

const optional = z.string().trim().max(120, "Use 120 characters or fewer");

const schema = z
  .object({
    institution: z
      .string()
      .trim()
      .min(1, "Where did you study?")
      .max(120, "Use 120 characters or fewer"),
    qualification: optional,
    field_of_study: optional,
    grade: optional,
    start_date: monthField,
    end_date: monthField,
  })
  .superRefine(checkDateOrder);

type Values = z.infer<typeof schema>;

const BLANK: Values = {
  institution: "",
  qualification: "",
  field_of_study: "",
  grade: "",
  start_date: "",
  end_date: "",
};

export function EducationSection({ education }: { education: Education[] }) {
  const [editing, setEditing] = useState<{ item: Education; index: number } | null>(null);
  const [adding, setAdding] = useState(false);
  const updateProfile = useUpdateProfile();

  async function save(next: Education[], success: string) {
    await updateProfile.mutateAsync({ education: next });
    toast.success(success);
  }

  async function onRemove(index: number) {
    try {
      await save(
        education.filter((_, position) => position !== index),
        "Education removed",
      );
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  return (
    <SectionCard
      id="education"
      title="Education"
      description="Where you study or studied. Every resume needs at least one."
      action={
        education.length > 0 ? (
          <Button variant="outline" size="sm" onClick={() => setAdding(true)}>
            <PlusIcon aria-hidden="true" />
            Add education
          </Button>
        ) : null
      }
    >
      {education.length === 0 ? (
        <div className="space-y-4">
          <EmptySectionNote>No education yet.</EmptySectionNote>
          <Button variant="outline" onClick={() => setAdding(true)}>
            <PlusIcon aria-hidden="true" />
            Add your school
          </Button>
        </div>
      ) : (
        <ul className="divide-y">
          {education.map((item, index) => (
            <li
              key={item.id ?? `${item.institution}-${index}`}
              className="flex items-start gap-4 py-4 first:pt-0 last:pb-0"
            >
              <div className="min-w-0 flex-1 space-y-1">
                <p className="font-medium">{item.institution}</p>
                {courseOf(item) ? <p className="text-sm">{courseOf(item)}</p> : null}
                <p className="text-sm text-muted-foreground">
                  {[
                    formatRange(item.start_date, item.end_date),
                    item.grade && `Grade: ${item.grade}`,
                  ]
                    .filter(Boolean)
                    .join(" · ") || "No dates given"}
                </p>
              </div>
              <div className="flex shrink-0 gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Edit ${item.institution}`}
                  onClick={() => setEditing({ item, index })}
                >
                  <PencilIcon aria-hidden="true" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Remove ${item.institution}`}
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

      <EducationDialog
        key={editing ? (editing.item.id ?? String(editing.index)) : "new"}
        open={adding || editing !== null}
        item={editing?.item ?? null}
        onClose={() => {
          setAdding(false);
          setEditing(null);
        }}
        onSubmit={async (values) => {
          const entry: Education = {
            ...(editing?.item ?? {}),
            institution: values.institution,
            qualification: orNull(values.qualification),
            field_of_study: orNull(values.field_of_study),
            grade: orNull(values.grade),
            start_date: orNull(values.start_date),
            end_date: orNull(values.end_date),
          };
          if (editing) {
            await save(
              education.map((current, index) => (index === editing.index ? entry : current)),
              "Education updated",
            );
          } else {
            await save([...education, entry], "Education added");
          }
        }}
      />
    </SectionCard>
  );
}

function courseOf(item: Education): string {
  return [item.qualification, item.field_of_study].filter(Boolean).join(", ");
}

function EducationDialog({
  open,
  item,
  onClose,
  onSubmit,
}: {
  open: boolean;
  item: Education | null;
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
          institution: item.institution,
          qualification: item.qualification ?? "",
          field_of_study: item.field_of_study ?? "",
          grade: item.grade ?? "",
          start_date: item.start_date ?? "",
          end_date: item.end_date ?? "",
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
            {item ? "Edit education" : "Add education"}
          </DialogTitle>
          <DialogDescription>
            Your school, and your course if you&apos;d like it on the page.
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

          <Field data-invalid={Boolean(errors.institution)}>
            <FieldLabel htmlFor="edu_institution">School</FieldLabel>
            <Input
              id="edu_institution"
              placeholder="University of Lagos"
              aria-invalid={Boolean(errors.institution)}
              {...register("institution")}
            />
            <FieldError errors={[errors.institution]} />
          </Field>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field data-invalid={Boolean(errors.qualification)}>
              <FieldLabel htmlFor="edu_qualification">Qualification (optional)</FieldLabel>
              <Input
                id="edu_qualification"
                placeholder="BSc"
                aria-invalid={Boolean(errors.qualification)}
                {...register("qualification")}
              />
              <FieldError errors={[errors.qualification]} />
            </Field>
            <Field data-invalid={Boolean(errors.field_of_study)}>
              <FieldLabel htmlFor="edu_field">Course (optional)</FieldLabel>
              <Input
                id="edu_field"
                placeholder="Computer Science"
                aria-invalid={Boolean(errors.field_of_study)}
                {...register("field_of_study")}
              />
              <FieldError errors={[errors.field_of_study]} />
            </Field>
          </div>

          <Field data-invalid={Boolean(errors.grade)}>
            <FieldLabel htmlFor="edu_grade">Grade or CGPA (optional)</FieldLabel>
            <Input
              id="edu_grade"
              placeholder="4.52/5, or Second Class Upper"
              aria-invalid={Boolean(errors.grade)}
              {...register("grade")}
            />
            {errors.grade ? (
              <FieldError errors={[errors.grade]} />
            ) : (
              <FieldDescription>Exactly as it appears on your transcript.</FieldDescription>
            )}
          </Field>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field data-invalid={Boolean(errors.start_date)}>
              <FieldLabel htmlFor="edu_start">Started (optional)</FieldLabel>
              <Input
                id="edu_start"
                placeholder="2022"
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
              <FieldLabel htmlFor="edu_end">Finished, or expected (optional)</FieldLabel>
              <Input
                id="edu_end"
                placeholder="2026"
                inputMode="numeric"
                aria-invalid={Boolean(errors.end_date)}
                {...register("end_date")}
              />
              <FieldError errors={[errors.end_date]} />
            </Field>
          </div>

          <DialogFooter showCloseButton>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : null}
              {isSubmitting ? "Saving…" : item ? "Save changes" : "Add education"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
