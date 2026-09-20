import type { Metadata } from "next";

import { AdminView } from "@/features/support/components/admin-view";

export const metadata: Metadata = { title: "Dashboard" };

export default function AdminPage() {
  return <AdminView />;
}
