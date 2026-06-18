"use client";

import { useCallback, useEffect, useState } from "react";
import type { DashboardData } from "@/lib/types";
import { LiveSitesModal, liveSiteCount } from "@/components/live-sites-modal";
import { AiDashboard } from "@/components/ai-dashboard";
import { DashboardTabs, type DashboardTab } from "@/components/dashboard-tabs";
import { BreakdownCharts } from "@/components/breakdown-charts";
import { LeadsTable } from "@/components/leads-table";
import { MarketCoverageGrid } from "@/components/market-coverage";
import { PipelineFunnel } from "@/components/pipeline-funnel";
import { RunsTable } from "@/components/runs-table";
import { StatsGrid } from "@/components/stats-grid";
import { ExternalLink, formatRelative } from "@/components/ui";

export function DashboardShell() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [liveSitesOpen, setLiveSitesOpen] = useState(false);
  const [tab, setTab] = useState<DashboardTab>("pipeline");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/dashboard", { cache: "no-store" });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const json = (await res.json()) as DashboardData;
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 60_000);
    return () => clearInterval(id);
  }, [load]);

  if (loading && !data) {
    return (
      <main className="mx-auto max-w-[1400px] px-4 py-16 text-center text-ink-400">
        Loading founder dashboard…
      </main>
    );
  }

  if (error && !data) {
    return (
      <main className="mx-auto max-w-lg px-4 py-16 text-center">
        <p className="text-signal-red">{error}</p>
        <button
          onClick={load}
          className="mt-4 rounded-xl bg-white/10 px-4 py-2 text-sm hover:bg-white/15"
        >
          Retry
        </button>
      </main>
    );
  }

  if (!data) return null;

  const marketsTotal = data.markets.niches.length * data.markets.cities.length;
  const liveCount = liveSiteCount(data.leads);

  return (
    <div className="min-h-screen">
      <LiveSitesModal
        leads={data.leads}
        open={liveSitesOpen}
        onClose={() => setLiveSitesOpen(false)}
        orgName={data.links.kemOrg?.split("/").pop() ?? "kem-llc"}
      />
      <header className="sticky top-0 z-20 border-b border-white/[0.06] bg-ink-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-4 px-4 py-4 md:px-6">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-signal-blue">
              Web Auto · Founder Monitor
            </p>
            <h1 className="text-xl font-semibold text-ink-100">Pipeline command center</h1>
            <p className="text-xs text-ink-500">
              Parallel niche scrape → merge → kem-llc deploy · updated {formatRelative(data.fetchedAt)}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {data.links.sheets && (
              <a
                href={data.links.sheets}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-ink-200 hover:bg-white/10"
              >
                Google Sheet
              </a>
            )}
            {data.links.actions && (
              <a
                href={data.links.actions}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-ink-200 hover:bg-white/10"
              >
                Run pipeline
              </a>
            )}
            <button
              type="button"
              onClick={() => setLiveSitesOpen(true)}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-ink-200 hover:bg-white/10"
            >
              kem-llc sites{liveCount > 0 ? ` (${liveCount})` : ""}
            </button>
            <button
              onClick={load}
              disabled={loading}
              className="rounded-lg bg-signal-blue px-3 py-2 text-xs font-medium text-ink-950 hover:brightness-110 disabled:opacity-60"
            >
              {loading ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </div>
        <div className="mx-auto max-w-[1400px] border-t border-white/[0.04] px-4 py-3 md:px-6">
          <DashboardTabs active={tab} onChange={setTab} />
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] space-y-6 px-4 py-6 md:px-6 md:py-8">
        {data.errors.length > 0 && (
          <div className="rounded-xl border border-signal-amber/30 bg-signal-amber/10 px-4 py-3 text-sm text-signal-amber">
            <p className="font-medium">Partial data — some sources failed:</p>
            <ul className="mt-1 list-inside list-disc text-signal-amber/90">
              {data.errors.map((err) => (
                <li key={err}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        <StatsGrid
          stats={data.stats}
          runSummary={data.runSummary}
          marketsTotal={marketsTotal}
        />

        {tab === "pipeline" ? (
          <>
            <div className="grid gap-4 xl:grid-cols-3">
              <div className="xl:col-span-1">
                <PipelineFunnel stats={data.stats} />
              </div>
              <div className="xl:col-span-2">
                <BreakdownCharts byNiche={data.byNiche} byCity={data.byCity} />
              </div>
            </div>

            <RunsTable runs={data.runs} />
            <LeadsTable leads={data.leads} />
            <MarketCoverageGrid coverage={data.coverage} />
          </>
        ) : (
          <AiDashboard aiCost={data.aiCost} stats={data.stats} />
        )}

        <footer className="border-t border-white/[0.06] pt-6 text-center text-xs text-ink-600">
          Deploy branch: <span className="font-mono text-ink-400">monitor</span>
          {data.links.repo && (
            <>
              {" "}
              · <ExternalLink href={data.links.repo}>GitHub repo</ExternalLink>
            </>
          )}
        </footer>
      </main>
    </div>
  );
}
