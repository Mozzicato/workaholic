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
import { useCreateResume } from "@/features/resumes/hooks";
import { ApiError, errorMessage } from "@/lib/api/errors";

const schema = z.object({
  title: z
    .string()
    .trim()
    .min(1, "Give this resume a name")
    .max(120, "Use 120 characters or fewer"),
  target_role: z.string().trim().max(120, "Use 120 characters or fewer"),
});

type Values = z.infer<typeof schema>;

export function CreateResumeDialog({ variant = "default" }: { variant?: "default" | "outline" }) {
  const [open, setOpen] = useState(false);
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
      });
      setOpen(false);
      reset();
      router.push(`/resumes/${resume.id}`);
    } catch (error) {
      // A duplicate name is the one case worth pointing at the field.
      setFormError(
        error instanceof ApiError && error.status === 409
          ? "You already have a resume with that name."
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
            Create resume
          </Button>
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-heading text-2xl">Start a resume</DialogTitle>
          <DialogDescription>
            Name it for yourself, and say which role it&apos;s for. Workaholic builds the content
            from what you tell it — nothing is invented.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <FieldGroup>
            <FormErrorAlert message={formError} />

            <Field data-invalid={Boolean(errors.title)}>
              <FieldLabel htmlFor="title">Name</FieldLabel>
              <Input
                id="title"
                className="h-10"
                placeholder="Software engineering resume"
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
                <FieldDescription>Used later to tailor and check the resume.</FieldDescription>
              )}
            </Field>

            <DialogFooter showCloseButton>
              <Button type="submit" size="lg" className="h-10" disabled={isSubmitting}>
                {isSubmitting ? <Spinner /> : null}
                {isSubmitting ? "Creating…" : "Create resume"}
              </Button>
            </DialogFooter>
          </FieldGroup>
        </form>
      </DialogContent>
    </Dialog>
  );
}
