"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUpIcon } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Spinner } from "@/components/ui/spinner";
import { profileKeys } from "@/features/profile/hooks";
import {
  acceptImport,
  importDocument,
  type ImportContents,
  type ImportProposal,
} from "@/features/profile/import-api";
import { getApiClient } from "@/lib/api/browser";
import { errorMessage } from "@/lib/api/errors";

import { SectionCard } from "./section-card";

const ACCEPT =
  ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

/**
 * Start from an existing resume (PRD §37).
 *
 * Upload → read → propose → the person ticks what is true → only that is added. A mis-parse or
 * something the document never said cannot reach the record without passing their eyes first.
 */
export function ImportSection() {
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [proposal, setProposal] = useState<ImportProposal | null>(null);
  const [chosen, setChosen] = useState<Record<string, boolean>>({});

  const upload = useMutation({
    mutationFn: (file: File) => importDocument(getApiClient(), file),
    onSuccess: (result) => {
      setProposal(result);
      setChosen(Object.fromEntries(keysOf(result.contents).map((key) => [key, true])));
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const accept = useMutation({
    mutationFn: (contents: ImportContents) => acceptImport(getApiClient(), contents),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: profileKeys.profile });
      setProposal(null);
      toast.success(
        result.added.length > 0
          ? `Added ${result.added.length} item${result.added.length === 1 ? "" : "s"} to your record`
          : "Everything was already in your record",
      );
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <SectionCard
      id="import"
      title="Start from an existing resume"
      description="Upload a PDF or Word file. We read it and show you what it says — you choose what goes into your record, and nothing is added until you do."
    >
      {proposal ? (
        <Review
          proposal={proposal}
          chosen={chosen}
          onToggle={(key) => setChosen((current) => ({ ...current, [key]: !current[key] }))}
          onCancel={() => setProposal(null)}
          accepting={accept.isPending}
          onAccept={() => accept.mutate(selected(proposal.contents, chosen))}
        />
      ) : (
        <div>
          <input
            ref={input}
            type="file"
            accept={ACCEPT}
            className="sr-only"
            aria-label="Choose a resume to upload"
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file) upload.mutate(file);
            }}
          />
          <Button
            variant="outline"
            disabled={upload.isPending}
            onClick={() => input.current?.click()}
          >
            {upload.isPending ? <Spinner /> : <FileUpIcon aria-hidden="true" />}
            {upload.isPending ? "Reading it…" : "Upload a resume"}
          </Button>
          <p className="mt-2 text-xs text-muted-foreground">
            PDF or DOCX, up to 8 MB. The file itself isn&apos;t kept — only what you choose to add.
          </p>
        </div>
      )}
    </SectionCard>
  );
}

function Review({
  proposal,
  chosen,
  onToggle,
  onCancel,
  onAccept,
  accepting,
}: {
  proposal: ImportProposal;
  chosen: Record<string, boolean>;
  onToggle: (key: string) => void;
  onCancel: () => void;
  onAccept: () => void;
  accepting: boolean;
}) {
  const { contents } = proposal;
  const empty = keysOf(contents).length === 0;
  const count = Object.values(chosen).filter(Boolean).length;

  if (empty) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          We couldn&apos;t find anything we could confirm from that document. You can add your
          experience below, or try another file.
        </p>
        <Button variant="outline" onClick={onCancel}>
          Try another file
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        Untick anything that isn&apos;t right. Only what stays ticked is added.
      </p>

      {contents.roles.length > 0 ? (
        <Group title="Roles">
          {contents.roles.map((role, index) => (
            <Choice
              key={`role-${index}`}
              id={`role-${index}`}
              checked={Boolean(chosen[`role-${index}`])}
              onToggle={onToggle}
              label={[role.title, role.employer].filter(Boolean).join(" at ")}
              detail={[
                [role.start_date, role.end_date].filter(Boolean).join(" – "),
                ...role.bullets,
              ]
                .filter(Boolean)
                .join(" · ")}
            />
          ))}
        </Group>
      ) : null}

      {contents.projects.length > 0 ? (
        <Group title="Projects">
          {contents.projects.map((project, index) => (
            <Choice
              key={`project-${index}`}
              id={`project-${index}`}
              checked={Boolean(chosen[`project-${index}`])}
              onToggle={onToggle}
              label={project.name}
              detail={project.description}
            />
          ))}
        </Group>
      ) : null}

      {contents.education.length > 0 ? (
        <Group title="Education">
          {contents.education.map((entry, index) => (
            <Choice
              key={`education-${index}`}
              id={`education-${index}`}
              checked={Boolean(chosen[`education-${index}`])}
              onToggle={onToggle}
              label={[entry.qualification, entry.institution].filter(Boolean).join(", ")}
              detail={[entry.start_date, entry.end_date].filter(Boolean).join(" – ")}
            />
          ))}
        </Group>
      ) : null}

      {contents.skills.length > 0 ? (
        <Group title="Skills">
          {contents.skills.map((skill, index) => (
            <Choice
              key={`skill-${index}`}
              id={`skill-${index}`}
              checked={Boolean(chosen[`skill-${index}`])}
              onToggle={onToggle}
              label={skill}
            />
          ))}
        </Group>
      ) : null}

      {proposal.dropped.length > 0 ? (
        <p className="text-xs text-muted-foreground">
          Left out, because the document didn&apos;t say it: {proposal.dropped.join("; ")}
        </p>
      ) : null}

      <div className="flex flex-wrap justify-end gap-3">
        <Button variant="ghost" onClick={onCancel} disabled={accepting}>
          Discard
        </Button>
        <Button onClick={onAccept} disabled={accepting || count === 0}>
          {accepting ? <Spinner /> : null}
          Add {count} to my record
        </Button>
      </div>
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">{title}</legend>
      <ul className="space-y-2">{children}</ul>
    </fieldset>
  );
}

function Choice({
  id,
  label,
  detail,
  checked,
  onToggle,
}: {
  id: string;
  label: string;
  detail?: string;
  checked: boolean;
  onToggle: (key: string) => void;
}) {
  const inputId = `import-${id}`;
  return (
    <li className="flex items-start gap-3">
      <Checkbox
        id={inputId}
        checked={checked}
        onCheckedChange={() => onToggle(id)}
        className="mt-0.5"
      />
      <label htmlFor={inputId} className="min-w-0 flex-1 text-sm">
        <span className="font-medium">{label}</span>
        {detail ? <span className="block text-xs text-muted-foreground">{detail}</span> : null}
      </label>
    </li>
  );
}

/** Every item a person can tick, keyed stably so the choice survives re-renders. */
function keysOf(contents: ImportContents): string[] {
  return [
    ...contents.roles.map((_, index) => `role-${index}`),
    ...contents.projects.map((_, index) => `project-${index}`),
    ...contents.education.map((_, index) => `education-${index}`),
    ...contents.skills.map((_, index) => `skill-${index}`),
  ];
}

/** The proposal, reduced to what the person left ticked. Contact details come with it. */
function selected(contents: ImportContents, chosen: Record<string, boolean>): ImportContents {
  return {
    ...contents,
    roles: contents.roles.filter((_, index) => chosen[`role-${index}`]),
    projects: contents.projects.filter((_, index) => chosen[`project-${index}`]),
    education: contents.education.filter((_, index) => chosen[`education-${index}`]),
    skills: contents.skills.filter((_, index) => chosen[`skill-${index}`]),
  };
}
