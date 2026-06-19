"use client";

import Link from "next/link";
import { liveSiteCount } from "@/components/live-sites-panel";
import { DashboardNav } from "@/components/dashboard-nav";
import { useDashboard } from "@/components/dashboard-provider";
import { ExternalLink, formatRelative } from "@/components/ui";

export function DashboardChrome({ children }: { children: React.ReactNode }) {
  const { data, loading, error, reload } = useDashboard();

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
          onClick={reload}
          className="mt-4 rounded-xl bg-white/10 px-4 py-2 text-sm hover:bg-white/15"
        >
          Retry
        </button>
      </main>
    );
  }

  if (!data) return null;

  const liveCount = liveSiteCount(data.leads);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-white/[0.06] bg-ink-950/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-4 px-4 py-4 md:px-6">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-signal-blue">
              Web Auto · Founder Monitor
            </p>
            <h1 className="text-xl font-semibold text-ink-100">Pipeline command center</h1>
            <p className="text-xs text-ink-500">
              Updated {formatRelative(data.fetchedAt)} · {liveCount} live · {data.stats.total}{" "}
              leads
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
            <Link
              href="/sites"
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-ink-200 hover:bg-white/10"
            >
              kem-llc sites{liveCount > 0 ? ` (${liveCount})` : ""}
            </Link>
            <button
              onClick={reload}
              disabled={loading}
              className="rounded-lg bg-signal-blue px-3 py-2 text-xs font-medium text-ink-950 hover:brightness-110 disabled:opacity-60"
            >
              {loading ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </div>
        <DashboardNav />
      </header>

      <main className="mx-auto max-w-[1400px] px-4 py-6 md:px-6 md:py-8">
        {data.errors.length > 0 && (
          <div className="mb-6 rounded-xl border border-signal-amber/30 bg-signal-amber/10 px-4 py-3 text-sm text-signal-amber">
            <p className="font-medium">Partial data — some sources failed:</p>
            <ul className="mt-1 list-inside list-disc text-signal-amber/90">
              {data.errors.map((err) => (
                <li key={err}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        {children}

        <footer className="mt-8 border-t border-white/[0.06] pt-6 text-center text-xs text-ink-600">
          Tabbed dashboard · deploy branch{" "}
          <span className="font-mono text-ink-400">monitor</span>
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
