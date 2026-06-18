import type { PipelineStats } from "@/lib/types";

function StatCard({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: number | string;
  hint?: string;
  accent?: string;
}) {
  return (
    <div className="panel p-5">
      <p className="stat-label">{label}</p>
      <p className={`stat-value mt-2 ${accent ?? ""}`}>{value}</p>
      {hint && <p className="mt-2 text-xs text-ink-500">{hint}</p>}
    </div>
  );
}

export function StatsGrid({
  stats,
  runSummary,
  marketsTotal,
}: {
  stats: PipelineStats;
  runSummary: { successRate: number; failure: number; total: number };
  marketsTotal: number;
}) {
  const conversion =
    stats.total > 0 ? Math.round((stats.liveSites / stats.total) * 100) : 0;

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Leads in inventory" value={stats.total} hint="From Google Sheet" />
      <StatCard
        label="Live sites deployed"
        value={stats.liveSites}
        hint={`${conversion}% of leads have a live URL`}
        accent="text-signal-green"
      />
      <StatCard
        label="Copy generated"
        value={stats.copyDone}
        hint={`${stats.copyPending} pending · ${stats.readyToDeploy} ready to deploy`}
        accent="text-signal-violet"
      />
      <StatCard
        label="Pipeline success rate"
        value={`${runSummary.successRate}%`}
        hint={`${runSummary.failure} failed of ${runSummary.total} recent runs`}
        accent={runSummary.successRate >= 70 ? "text-signal-green" : "text-signal-amber"}
      />
      <StatCard
        label="Market combos"
        value={marketsTotal}
        hint="Niche × city targets configured"
      />
      <StatCard label="Scraped" value={stats.scraped} hint="Marked Done in sheet" />
      <StatCard
        label="Awaiting deploy"
        value={stats.readyToDeploy}
        hint="Copy done, no live URL yet"
        accent="text-signal-amber"
      />
      <StatCard
        label="Funnel gap"
        value={Math.max(0, stats.copyDone - stats.liveSites)}
        hint="Generated but not yet live"
      />
    </div>
  );
}
