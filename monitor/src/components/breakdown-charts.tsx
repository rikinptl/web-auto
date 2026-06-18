import type { NicheCount, CityCount } from "@/lib/types";
import { Panel } from "./ui";

function MiniBars({ items, emptyLabel }: { items: { label: string; count: number }[]; emptyLabel: string }) {
  if (!items.length) {
    return <p className="text-sm text-ink-500">{emptyLabel}</p>;
  }
  const max = items[0]?.count ?? 1;
  return (
    <div className="space-y-3">
      {items.slice(0, 8).map((item) => (
        <div key={item.label}>
          <div className="mb-1 flex justify-between gap-2 text-sm">
            <span className="truncate text-ink-300">{item.label}</span>
            <span className="font-mono text-ink-200">{item.count}</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-ink-800">
            <div
              className="h-full rounded-full bg-signal-blue/80"
              style={{ width: `${Math.round((item.count / max) * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function BreakdownCharts({
  byNiche,
  byCity,
}: {
  byNiche: NicheCount[];
  byCity: CityCount[];
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="By niche" subtitle="Lead distribution">
        <MiniBars
          items={byNiche.map((n) => ({ label: n.niche || "Unknown", count: n.count }))}
          emptyLabel="No leads yet — run the pipeline"
        />
      </Panel>
      <Panel title="By city" subtitle="Geographic spread">
        <MiniBars
          items={byCity.map((c) => ({ label: c.city || "Unknown", count: c.count }))}
          emptyLabel="No city data yet"
        />
      </Panel>
    </div>
  );
}
