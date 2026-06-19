"use client";

import { useDashboard } from "@/components/dashboard-provider";
import { LeadsTable } from "@/components/leads-table";

export default function LeadsPage() {
  const { data } = useDashboard();
  if (!data) return null;
  return <LeadsTable leads={data.leads} />;
}
