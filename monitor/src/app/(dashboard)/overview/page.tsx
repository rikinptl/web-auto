"use client";

import { useDashboard } from "@/components/dashboard-provider";
import { BreakdownCharts } from "@/components/breakdown-charts";
import { PipelineFunnel } from "@/components/pipeline-funnel";
import { StatsGrid } from "@/components/stats-grid";

export default function OverviewPage() {
  const { data } = useDashboard();
  if (!data) return null;

  const marketsTotal = data.markets.niches.length * data.markets.cities.length;

  return (
    <div className="space-y-6">
      <StatsGrid stats={data.stats} runSummary={data.runSummary} marketsTotal={marketsTotal} />
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="xl:col-span-1">
          <PipelineFunnel stats={data.stats} />
        </div>
        <div className="xl:col-span-2">
          <BreakdownCharts byNiche={data.byNiche} byCity={data.byCity} />
        </div>
      </div>
    </div>
  );
}
