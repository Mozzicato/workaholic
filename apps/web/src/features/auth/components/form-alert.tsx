import { CircleAlertIcon, MailCheckIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export function FormErrorAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <Alert variant="destructive" className="border-destructive/30">
      <CircleAlertIcon aria-hidden="true" />
      <AlertDescription className="text-destructive">{message}</AlertDescription>
    </Alert>
  );
}

export function CheckInboxAlert({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Alert className="border-primary/25 bg-accent/60">
      <MailCheckIcon aria-hidden="true" className="text-primary" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{children}</AlertDescription>
    </Alert>
  );
}
