"use client";

import { useMemo, useState } from "react";
import type { Lead } from "@/lib/types";
import { formatDuration, formatUsd, leadKey } from "@/lib/format";

export function LiveSitesPanel({
  leads,
  orgName = "kem-llc",
  costPerSiteUsd = 0.03,
  tokensPerSite = 4500,
}: {
  leads: Lead[];
  orgName?: string;
  costPerSiteUsd?: number;
  tokensPerSite?: number;
}) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  const liveLeads = useMemo(
    () =>
      leads
        .filter((lead) => lead.liveUrl?.trim().startsWith("http"))
        .sort((a, b) => a.name.localeCompare(b.name)),
    [leads]
  );

  if (liveLeads.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-ink-500">
        No live URLs in the sheet yet. Run the pipeline or backfill pending rows.
      </p>
    );
  }

  return (
    <div>
      <p className="mb-4 text-sm text-ink-400">
        {liveLeads.length} deployed on {orgName} · click a business for Maps link, build time, and
        est. cost
      </p>
      <ul className="space-y-1">
        {liveLeads.map((lead) => {
          const key = leadKey(lead);
          const expanded = expandedKey === key;
          const mapsUrl = lead.mapsUrl?.trim() ?? "";
          const hasMaps = mapsUrl.startsWith("http");

          return (
            <li
              key={key}
              className="rounded-xl border border-transparent transition-colors hover:border-white/[0.04]"
            >
              <button
                type="button"
                onClick={() => setExpandedKey(expanded ? null : key)}
                aria-expanded={expanded}
                className="flex w-full flex-col gap-1 rounded-xl px-3 py-3 text-left transition hover:bg-white/[0.04] sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-ink-100">{lead.name}</p>
                  <p className="text-xs text-ink-500">
                    {lead.niche || "—"}
                    {lead.city ? ` · ${lead.city}` : ""}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2 sm:justify-end">
                  <span className="hidden text-[10px] font-medium uppercase tracking-wide text-ink-500 sm:inline">
                    {expanded ? "Hide" : "Details"}
                  </span>
                  {lead.deployDurationSec != null && (
                    <span className="rounded-md bg-white/5 px-2 py-0.5 font-mono text-[10px] text-ink-400">
                      {formatDuration(lead.deployDurationSec)}
                    </span>
                  )}
                  <span
                    className={`inline-flex h-6 w-6 items-center justify-center rounded-md bg-white/5 text-xs text-ink-400 transition ${expanded ? "rotate-180 bg-signal-blue/15 text-signal-blue" : ""}`}
                    aria-hidden
                  >
                    ▾
                  </span>
                </div>
              </button>

              {expanded && (
                <div className="mx-3 mb-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                  <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-ink-500">
                        Live site
                      </dt>
                      <dd className="mt-1">
                        <a
                          href={lead.liveUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="break-all font-mono text-xs text-signal-green hover:underline"
                        >
                          {lead.liveUrl.replace(/^https?:\/\//, "")}
                        </a>
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-ink-500">
                        Google Maps
                      </dt>
                      <dd className="mt-1">
                        {hasMaps ? (
                          <a
                            href={mapsUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-signal-blue hover:underline"
                          >
                            Open listing
                          </a>
                        ) : (
                          <span className="text-xs text-ink-500">Not in sheet</span>
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-ink-500">
                        Site created
                      </dt>
                      <dd className="mt-1 text-xs text-ink-200">{lead.siteCreatedAt || "—"}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-ink-500">
                        Build time
                      </dt>
                      <dd className="mt-1 font-mono text-ink-200">
                        {formatDuration(lead.deployDurationSec)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-ink-500">
                        Est. AI cost
                      </dt>
                      <dd className="mt-1 font-mono text-ink-200">{formatUsd(costPerSiteUsd)}</dd>
                      <p className="mt-0.5 text-[10px] text-ink-600">
                        ~{tokensPerSite.toLocaleString()} tokens · env estimate
                      </p>
                    </div>
                  </dl>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <a
                      href={lead.liveUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-lg bg-signal-green/15 px-3 py-1.5 text-xs font-medium text-signal-green hover:bg-signal-green/20"
                    >
                      Open live site
                    </a>
                    {hasMaps && (
                      <a
                        href={mapsUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-ink-200 hover:bg-white/5"
                      >
                        Google Maps
                      </a>
                    )}
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function liveSiteCount(leads: Lead[]) {
  return leads.filter((lead) => lead.liveUrl?.trim().startsWith("http")).length;
}
