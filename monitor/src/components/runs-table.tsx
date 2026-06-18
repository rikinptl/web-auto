import type { WorkflowRun } from "@/lib/types";
import { ExternalLink, Panel, StatusBadge, formatDuration, formatRelative, statusKind } from "./ui";

export function RunsTable({ runs }: { runs: WorkflowRun[] }) {
  return (
    <Panel title="Pipeline runs" subtitle="Recent GitHub Actions workflow history">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[800px] border-collapse">
          <thead>
            <tr className="border-b border-white/10">
              <th className="table-head pb-3 pr-4">Run</th>
              <th className="table-head pb-3 pr-4">Mode</th>
              <th className="table-head pb-3 pr-4">Market</th>
              <th className="table-head pb-3 pr-4">Status</th>
              <th className="table-head pb-3 pr-4">Duration</th>
              <th className="table-head pb-3 pr-4">When</th>
              <th className="table-head pb-3">Log</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-sm text-ink-500">
                  No runs found. Set GITHUB_TOKEN to load Actions history.
                </td>
              </tr>
            ) : (
              runs.map((run) => (
                <tr key={run.id} className="border-b border-white/[0.04]">
                  <td className="table-cell pr-4">
                    <div className="font-medium text-ink-100">{run.name}</div>
                    <div className="font-mono text-xs text-ink-500">#{run.id}</div>
                  </td>
                  <td className="table-cell pr-4 text-xs text-ink-400">
                    {run.runMode === "all_niches" && (
                      <>All niches{run.maxResults ? ` · max ${run.maxResults}` : ""}</>
                    )}
                    {run.runMode === "single" && "Single niche"}
                    {run.runMode === "pending" && "Backfill"}
                    {run.runMode === "unknown" && "—"}
                  </td>
                  <td className="table-cell pr-4 text-sm text-ink-300">
                    {run.niche && run.city ? (
                      <>
                        {run.niche} · {run.city}
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="table-cell pr-4">
                    <StatusBadge
                      value={run.conclusion || run.status}
                      kind={statusKind(run.conclusion || run.status, "run")}
                    />
                  </td>
                  <td className="table-cell pr-4 font-mono text-xs">{formatDuration(run.durationSec)}</td>
                  <td className="table-cell pr-4 text-sm text-ink-400">{formatRelative(run.createdAt)}</td>
                  <td className="table-cell">
                    <ExternalLink href={run.htmlUrl}>View</ExternalLink>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
