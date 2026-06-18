import type { PipelineStats } from "@/lib/types";
import { Panel } from "./ui";

function Bar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-ink-300">{label}</span>
        <span className="font-mono text-ink-200">
          {value}
          <span className="text-ink-500"> ({pct}%)</span>
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-ink-800">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function PipelineFunnel({ stats }: { stats: PipelineStats }) {
  const max = Math.max(stats.total, 1);
  return (
    <Panel title="Lead funnel" subtitle="Parallel scrape → merge (50 cap) → DeepSeek → kem-llc Pages">
      <div className="space-y-4">
        <Bar label="In inventory" value={stats.total} max={max} color="bg-signal-blue" />
        <Bar label="Scraped" value={stats.scraped} max={max} color="bg-signal-violet" />
        <Bar label="Copy generated" value={stats.copyDone} max={max} color="bg-signal-amber" />
        <Bar label="Live on kem-llc Pages" value={stats.liveSites} max={max} color="bg-signal-green" />
      </div>
    </Panel>
  );
}
