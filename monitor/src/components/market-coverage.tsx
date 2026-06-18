"use client";

import { useMemo, useState } from "react";
import type { MarketCoverage } from "@/lib/types";
import { Panel, StatusBadge, formatRelative, statusKind } from "./ui";

export function MarketCoverageGrid({ coverage }: { coverage: MarketCoverage[] }) {
  const [phase, setPhase] = useState<number | "all">("all");

  const filtered = useMemo(() => {
    if (phase === "all") return coverage;
    return coverage.filter((c) => c.phase === phase);
  }, [coverage, phase]);

  const active = filtered.filter((c) => c.leadCount > 0 || c.lastRunAt).length;
  const live = filtered.filter((c) => c.liveCount > 0).length;

  return (
    <Panel
      title="Market coverage"
      subtitle={`${active} markets touched · ${live} with live sites`}
      action={
        <div className="flex gap-2">
          {(["all", 1, 2, 3] as const).map((p) => (
            <button
              key={String(p)}
              onClick={() => setPhase(p)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                phase === p
                  ? "bg-signal-violet/20 text-signal-violet"
                  : "bg-white/5 text-ink-400 hover:text-ink-200"
              }`}
            >
              {p === "all" ? "All" : `Phase ${p}`}
            </button>
          ))}
        </div>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {filtered.map((cell) => {
          const touched = cell.leadCount > 0 || cell.lastRunAt;
          return (
            <div
              key={`${cell.nicheId}-${cell.cityId}`}
              className={`rounded-xl border p-4 transition ${
                cell.liveCount > 0
                  ? "border-signal-green/30 bg-signal-green/5"
                  : touched
                    ? "border-signal-amber/20 bg-white/[0.02]"
                    : "border-white/[0.06] bg-ink-900/40"
              }`}
            >
              <div className="mb-2 flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-ink-100">{cell.nicheLabel}</p>
                  <p className="text-xs text-ink-400">{cell.cityLabel}</p>
                </div>
                <span className="rounded-md bg-white/5 px-1.5 py-0.5 text-[10px] text-ink-500">
                  P{cell.phase}
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <span className="text-ink-400">
                  <span className="font-mono text-ink-200">{cell.leadCount}</span> leads
                </span>
                <span className="text-ink-600">·</span>
                <span className="text-ink-400">
                  <span className="font-mono text-signal-green">{cell.liveCount}</span> live
                </span>
              </div>
              {cell.lastRunAt ? (
                <div className="mt-3 flex items-center justify-between gap-2">
                  <span className="text-[11px] text-ink-500">{formatRelative(cell.lastRunAt)}</span>
                  <StatusBadge
                    value={cell.lastRunStatus || "—"}
                    kind={statusKind(cell.lastRunStatus, "run")}
                  />
                </div>
              ) : (
                <p className="mt-3 text-[11px] text-ink-600">Not run yet</p>
              )}
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
