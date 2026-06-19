"use client";

import { useDashboard } from "@/components/dashboard-provider";
import { MarketCoverageGrid } from "@/components/market-coverage";

export default function MarketsPage() {
  const { data } = useDashboard();
  if (!data) return null;
  return <MarketCoverageGrid coverage={data.coverage} />;
}
