"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { FormErrorAlert } from "@/features/auth/components/form-alert";
import type { Basics } from "@/features/profile/api";
import { useUpdateProfile } from "@/features/profile/hooks";
import { orNull } from "@/features/profile/lines";
import { errorMessage } from "@/lib/api/errors";

import { SectionCard } from "./section-card";

const schema = z.object({
  full_name: z.string().trim().max(120, "Use 120 characters or fewer"),
  headline: z.string().trim().max(200, "Use 200 characters or fewer"),
  email: z.union([z.literal(""), z.email("Enter a valid email address")]),
  phone: z.string().trim().max(40, "Use 40 characters or fewer"),
  location: z.string().trim().max(120, "Use 120 characters or fewer"),
  summary: z.string().trim().max(2000, "Use 2000 characters or fewer"),
});

type Values = z.infer<typeof schema>;

function toValues(basics: Basics): Values {
  return {
    full_name: basics.full_name ?? "",
    headline: basics.headline ?? "",
    email: basics.email ?? "",
    phone: basics.phone ?? "",
    location: basics.location ?? "",
    summary: basics.summary ?? "",
  };
}

export function BasicsForm({ basics }: { basics: Basics }) {
  const updateProfile = useUpdateProfile();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: toValues(basics),
  });

  // Keep the form in step with the server copy after a save or a refetch.
  useEffect(() => {
    reset(toValues(basics));
  }, [basics, reset]);

  async function onSubmit(values: Values) {
    try {
      await updateProfile.mutateAsync({
        basics: {
          full_name: orNull(values.full_name),
          headline: orNull(values.headline),
          email: orNull(values.email),
          phone: orNull(values.phone),
          location: orNull(values.location),
          summary: orNull(values.summary),
        },
      });
      toast.success("Details saved");
    } catch (error) {
      setError("root", { message: errorMessage(error) });
    }
  }

  return (
    <SectionCard
      id="basics"
      title="About you"
      description="Contact details and a short summary, used at the top of every resume you build."
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
        <FormErrorAlert message={errors.root?.message ?? null} />

        <div className="grid gap-5 sm:grid-cols-2">
          <TextField
            id="full_name"
            label="Full name"
            placeholder="Ada Lovelace"
            error={errors.full_name?.message}
            {...register("full_name")}
          />
          <TextField
            id="headline"
            label="Headline"
            placeholder="Backend engineer"
            error={errors.headline?.message}
            {...register("headline")}
          />
          <TextField
            id="profile_email"
            label="Contact email"
            type="email"
            placeholder="you@example.com"
            error={errors.email?.message}
            {...register("email")}
          />
          <TextField
            id="phone"
            label="Phone"
            placeholder="+234 800 000 0000"
            error={errors.phone?.message}
            {...register("phone")}
          />
          <TextField
            id="location"
            label="Location"
            placeholder="Lagos, Nigeria"
            error={errors.location?.message}
            {...register("location")}
          />
        </div>

        <Field data-invalid={Boolean(errors.summary)}>
          <FieldLabel htmlFor="summary">Summary</FieldLabel>
          <Textarea
            id="summary"
            rows={4}
            placeholder="What you do, and what you're looking for."
            aria-invalid={Boolean(errors.summary)}
            {...register("summary")}
          />
          {errors.summary ? (
            <FieldError errors={[errors.summary]} />
          ) : (
            <FieldDescription>
              Written in your words. Workaholic will not add claims you haven&apos;t made.
            </FieldDescription>
          )}
        </Field>

        <div className="flex justify-end">
          <Button type="submit" disabled={isSubmitting || !isDirty}>
            {isSubmitting ? <Spinner /> : null}
            {isSubmitting ? "Saving…" : "Save details"}
          </Button>
        </div>
      </form>
    </SectionCard>
  );
}

function TextField({
  id,
  label,
  error,
  ...props
}: React.ComponentProps<typeof Input> & {
  id: string;
  label: string;
  error?: string;
}) {
  return (
    <Field data-invalid={Boolean(error)}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Input id={id} aria-invalid={Boolean(error)} {...props} />
      {error ? <FieldError errors={[{ message: error }]} /> : null}
    </Field>
  );
}
