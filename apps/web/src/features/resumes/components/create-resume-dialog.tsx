"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { PlusIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { FormErrorAlert } from "@/features/auth/components/form-alert";
import type { DocumentType } from "@/features/resumes/api";
import { useCreateResume } from "@/features/resumes/hooks";
import { ApiError, errorMessage } from "@/lib/api/errors";
import { cn } from "@/lib/utils";

const schema = z.object({
  title: z
    .string()
    .trim()
    .min(1, "Give this document a name")
    .max(120, "Use 120 characters or fewer"),
  target_role: z.string().trim().max(120, "Use 120 characters or fewer"),
});

const KINDS = [
  { value: "resume", label: "Resume", description: "Your experience, on one page" },
  { value: "cover_letter", label: "Cover letter", description: "A letter for one application" },
] as const satisfies readonly { value: DocumentType; label: string; description: string }[];

type Values = z.infer<typeof schema>;

export function CreateResumeDialog({ variant = "default" }: { variant?: "default" | "outline" }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<DocumentType>("resume");
  const [formError, setFormError] = useState<string | null>(null);
  const router = useRouter();
  const createResume = useCreateResume();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { title: "", target_role: "" },
  });

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      const resume = await createResume.mutateAsync({
        title: values.title,
        target_role: values.target_role || null,
        document_type: kind,
      });
      setOpen(false);
      reset();
      router.push(`/resumes/${resume.id}`);
    } catch (error) {
      // A duplicate name is the one case worth pointing at the field.
      setFormError(
        error instanceof ApiError && error.status === 409
          ? "You already have a document with that name."
          : errorMessage(error),
      );
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setFormError(null);
      }}
    >
      <DialogTrigger
        render={
          <Button size="lg" variant={variant} className="h-10">
            <PlusIcon aria-hidden="true" />
            Create
          </Button>
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-heading text-2xl">Start something new</DialogTitle>
          <DialogDescription>
            Name it for yourself, and say which role it&apos;s for. Workaholic builds the content
            from what you tell it — nothing is invented.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <FieldGroup>
            <FormErrorAlert message={formError} />

            <fieldset>
              <legend className="text-sm font-medium">What are you making?</legend>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                {KINDS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    aria-pressed={kind === option.value}
                    onClick={() => setKind(option.value)}
                    className={cn(
                      "rounded-lg border px-3 py-2.5 text-left transition-colors outline-none",
                      "focus-visible:ring-3 focus-visible:ring-ring/50",
                      kind === option.value ? "border-primary bg-accent" : "hover:bg-muted/60",
                    )}
                  >
                    <span className="block text-sm font-medium">{option.label}</span>
                    <span className="block text-xs text-muted-foreground">
                      {option.description}
                    </span>
                  </button>
                ))}
              </div>
            </fieldset>

            <Field data-invalid={Boolean(errors.title)}>
              <FieldLabel htmlFor="title">Name</FieldLabel>
              <Input
                id="title"
                className="h-10"
                placeholder={kind === "resume" ? "Software engineering resume" : "Northwind letter"}
                aria-invalid={Boolean(errors.title)}
                {...register("title")}
              />
              <FieldError errors={[errors.title]} />
            </Field>

            <Field data-invalid={Boolean(errors.target_role)}>
              <FieldLabel htmlFor="target_role">Target role (optional)</FieldLabel>
              <Input
                id="target_role"
                className="h-10"
                placeholder="Junior Backend Engineer"
                aria-invalid={Boolean(errors.target_role)}
                {...register("target_role")}
              />
              {errors.target_role ? (
                <FieldError errors={[errors.target_role]} />
              ) : (
                <FieldDescription>
                  {kind === "resume"
                    ? "Used later to tailor and check the resume."
                    : "The role the letter is for."}
                </FieldDescription>
              )}
            </Field>

            <DialogFooter showCloseButton>
              <Button type="submit" size="lg" className="h-10" disabled={isSubmitting}>
                {isSubmitting ? <Spinner /> : null}
                {isSubmitting ? "Creating…" : kind === "resume" ? "Create resume" : "Create letter"}
              </Button>
            </DialogFooter>
          </FieldGroup>
        </form>
      </DialogContent>
    </Dialog>
  );
}
