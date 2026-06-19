"use client";

import { useDashboard } from "@/components/dashboard-provider";
import { AiDashboard } from "@/components/ai-dashboard";

export default function AiPage() {
  const { data } = useDashboard();
  if (!data) return null;
  return <AiDashboard aiCost={data.aiCost} stats={data.stats} />;
}
