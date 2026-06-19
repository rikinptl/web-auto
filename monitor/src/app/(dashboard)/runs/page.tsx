"use client";

import { useDashboard } from "@/components/dashboard-provider";
import { RunsTable } from "@/components/runs-table";

export default function RunsPage() {
  const { data } = useDashboard();
  if (!data) return null;
  return <RunsTable runs={data.runs} />;
}
