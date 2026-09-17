"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { PencilIcon, PlusIcon, Trash2Icon } from "lucide-react";
import { useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
import type { Experience } from "@/features/profile/api";
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
    employer: z.string().trim().min(1, "Who was this for?").max(120, "Use 120 characters or fewer"),
    title: z.string().trim().min(1, "What was your role?").max(120, "Use 120 characters or fewer"),
    location: z.string().trim().max(120, "Use 120 characters or fewer"),
    is_current: z.boolean(),
    start_date: monthField,
    end_date: monthField,
    bullets: z.string(),
    technologies: z.string(),
  })
  .superRefine((values, ctx) => {
    checkDateOrder(values, ctx);
    if (values.is_current && values.end_date) {
      ctx.addIssue({
        code: "custom",
        path: ["end_date"],
        message: "Leave this empty while the role is current",
      });
    }
  });

type Values = z.infer<typeof schema>;

const BLANK: Values = {
  employer: "",
  title: "",
  location: "",
  is_current: false,
  start_date: "",
  end_date: "",
  bullets: "",
  technologies: "",
};

export function ExperienceSection({ experience }: { experience: Experience[] }) {
  const [editing, setEditing] = useState<{
    item: Experience;
    index: number;
  } | null>(null);
  const [adding, setAdding] = useState(false);
  const updateProfile = useUpdateProfile();

  async function save(next: Experience[], success: string) {
    await updateProfile.mutateAsync({ experience: next });
    toast.success(success);
  }

  async function onRemove(index: number) {
    try {
      await save(
        experience.filter((_, position) => position !== index),
        "Role removed",
      );
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  return (
    <SectionCard
      id="experience"
      title="Experience"
      description="Roles you've held, and what you did in them. Write what happened; Workaholic will not add numbers you didn't give it."
      action={
        experience.length > 0 ? (
          <Button variant="outline" size="sm" onClick={() => setAdding(true)}>
            <PlusIcon aria-hidden="true" />
            Add role
          </Button>
        ) : null
      }
    >
      {experience.length === 0 ? (
        <div className="space-y-4">
          <EmptySectionNote>No roles yet.</EmptySectionNote>
          <Button variant="outline" onClick={() => setAdding(true)}>
            <PlusIcon aria-hidden="true" />
            Add your first role
          </Button>
        </div>
      ) : (
        <ul className="divide-y">
          {experience.map((item, index) => (
            <li
              key={item.id ?? `${item.employer}-${index}`}
              className="flex items-start gap-4 py-4 first:pt-0 last:pb-0"
            >
              <div className="min-w-0 flex-1 space-y-1">
                <p className="font-medium">
                  {item.title} · {item.employer}
                </p>
                <p className="text-sm text-muted-foreground">
                  {[formatRange(item.start_date, item.end_date, item.is_current), item.location]
                    .filter(Boolean)
                    .join(" · ") || "No dates given"}
                </p>
                {item.bullets.length > 0 ? (
                  <ul className="mt-2 space-y-1 text-sm leading-relaxed">
                    {item.bullets.map((bullet, position) => (
                      <li key={position} className="flex gap-2">
                        <span aria-hidden="true" className="text-muted-foreground">
                          •
                        </span>
                        <span>{bullet}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {item.technologies.length > 0 ? (
                  <p className="pt-1 text-sm text-muted-foreground">
                    {item.technologies.join(", ")}
                  </p>
                ) : null}
              </div>
              <div className="flex shrink-0 gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Edit ${item.title} at ${item.employer}`}
                  onClick={() => setEditing({ item, index })}
                >
                  <PencilIcon aria-hidden="true" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Remove ${item.title} at ${item.employer}`}
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

      <ExperienceDialog
        key={editing ? (editing.item.id ?? String(editing.index)) : "new"}
        open={adding || editing !== null}
        item={editing?.item ?? null}
        onClose={() => {
          setAdding(false);
          setEditing(null);
        }}
        onSubmit={async (values) => {
          const entry: Experience = {
            ...(editing?.item ?? {}),
            employer: values.employer,
            title: values.title,
            location: orNull(values.location),
            is_current: values.is_current,
            start_date: orNull(values.start_date),
            end_date: values.is_current ? null : orNull(values.end_date),
            bullets: fromLines(values.bullets),
            technologies: fromCommas(values.technologies),
          };
          if (editing) {
            await save(
              experience.map((current, index) => (index === editing.index ? entry : current)),
              "Role updated",
            );
          } else {
            await save([...experience, entry], "Role added");
          }
        }}
      />
    </SectionCard>
  );
}

function ExperienceDialog({
  open,
  item,
  onClose,
  onSubmit,
}: {
  open: boolean;
  item: Experience | null;
  onClose: () => void;
  onSubmit: (values: Values) => Promise<void>;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: item
      ? {
          employer: item.employer,
          title: item.title,
          location: item.location ?? "",
          is_current: item.is_current,
          start_date: item.start_date ?? "",
          end_date: item.end_date ?? "",
          bullets: toLines(item.bullets),
          technologies: toCommas(item.technologies),
        }
      : BLANK,
  });
  const isCurrent = useWatch({ control, name: "is_current" });

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
            {item ? "Edit role" : "Add a role"}
          </DialogTitle>
          <DialogDescription>
            Describe what you did in your own words. Anything you write here is treated as fact;
            anything you leave out stays out of your resumes.
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

          <div className="grid gap-5 sm:grid-cols-2">
            <Field data-invalid={Boolean(errors.title)}>
              <FieldLabel htmlFor="exp_title">Role</FieldLabel>
              <Input
                id="exp_title"
                placeholder="Backend Engineer"
                aria-invalid={Boolean(errors.title)}
                {...register("title")}
              />
              <FieldError errors={[errors.title]} />
            </Field>
            <Field data-invalid={Boolean(errors.employer)}>
              <FieldLabel htmlFor="exp_employer">Employer</FieldLabel>
              <Input
                id="exp_employer"
                placeholder="Paystack"
                aria-invalid={Boolean(errors.employer)}
                {...register("employer")}
              />
              <FieldError errors={[errors.employer]} />
            </Field>
            <Field data-invalid={Boolean(errors.location)}>
              <FieldLabel htmlFor="exp_location">Location (optional)</FieldLabel>
              <Input
                id="exp_location"
                placeholder="Lagos, Nigeria"
                aria-invalid={Boolean(errors.location)}
                {...register("location")}
              />
              <FieldError errors={[errors.location]} />
            </Field>
            <Field data-invalid={Boolean(errors.start_date)}>
              <FieldLabel htmlFor="exp_start">Started</FieldLabel>
              <Input
                id="exp_start"
                placeholder="2024-03"
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
              <FieldLabel htmlFor="exp_end">Ended</FieldLabel>
              <Input
                id="exp_end"
                placeholder="2025-06"
                inputMode="numeric"
                disabled={isCurrent}
                aria-invalid={Boolean(errors.end_date)}
                {...register("end_date")}
              />
              <FieldError errors={[errors.end_date]} />
            </Field>
            <Controller
              control={control}
              name="is_current"
              render={({ field }) => (
                <Field orientation="horizontal" className="sm:self-end sm:pb-2.5">
                  <Checkbox
                    id="exp_current"
                    checked={field.value}
                    onCheckedChange={(checked) => field.onChange(checked === true)}
                    onBlur={field.onBlur}
                  />
                  <FieldLabel htmlFor="exp_current" className="font-normal">
                    I still work here
                  </FieldLabel>
                </Field>
              )}
            />
          </div>

          <Field data-invalid={Boolean(errors.bullets)}>
            <FieldLabel htmlFor="exp_bullets">What you did</FieldLabel>
            <Textarea
              id="exp_bullets"
              rows={5}
              placeholder={"Built the payouts reconciliation service\nMentored two interns"}
              aria-invalid={Boolean(errors.bullets)}
              {...register("bullets")}
            />
            <FieldDescription>
              One per line. Include real numbers if you have them — none will be invented for you.
            </FieldDescription>
          </Field>

          <Field>
            <FieldLabel htmlFor="exp_tech">Tools used (optional)</FieldLabel>
            <Input
              id="exp_tech"
              placeholder="Python, PostgreSQL, Docker"
              {...register("technologies")}
            />
            <FieldDescription>Separated by commas.</FieldDescription>
          </Field>

          <DialogFooter showCloseButton>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : null}
              {isSubmitting ? "Saving…" : item ? "Save changes" : "Add role"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
