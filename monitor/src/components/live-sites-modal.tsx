"use client";

import { useEffect, useMemo, useState } from "react";
import type { Lead } from "@/lib/types";
import { formatDuration, formatUsd, leadKey } from "@/lib/format";

export function LiveSitesModal({
  leads,
  open,
  onClose,
  orgName = "kem-llc",
  costPerSiteUsd = 0.03,
  tokensPerSite = 4500,
}: {
  leads: Lead[];
  open: boolean;
  onClose: () => void;
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

  useEffect(() => {
    if (!open) {
      setExpandedKey(null);
      return;
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[8vh]">
      <button
        type="button"
        aria-label="Close"
        className="absolute inset-0 bg-ink-950/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-labelledby="live-sites-title"
        className="panel relative z-10 flex max-h-[min(80vh,720px)] w-full max-w-2xl flex-col shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] p-5">
          <div>
            <h2 id="live-sites-title" className="text-lg font-semibold text-ink-100">
              {orgName} live sites
            </h2>
            <p className="mt-1 text-sm text-ink-400">
              {liveLeads.length} deployed · click a business for links, build time, and est. cost
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-ink-300 hover:bg-white/5"
          >
            Close
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          {liveLeads.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-ink-500">
              No live URLs in the sheet yet. Run the pipeline or backfill pending rows.
            </p>
          ) : (
            <ul className="space-y-1">
              {liveLeads.map((lead) => {
                const key = leadKey(lead);
                const expanded = expandedKey === key;
                const mapsUrl = lead.mapsUrl?.trim() ?? "";
                const hasMaps = mapsUrl.startsWith("http");

                return (
                  <li key={key} className="rounded-xl border border-transparent transition-colors hover:border-white/[0.04]">
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
                        {lead.deployDurationSec != null && (
                          <span className="rounded-md bg-white/5 px-2 py-0.5 font-mono text-[10px] text-ink-400">
                            {formatDuration(lead.deployDurationSec)}
                          </span>
                        )}
                        <span
                          className={`text-ink-500 transition ${expanded ? "rotate-180" : ""}`}
                          aria-hidden
                        >
                          ▾
                        </span>
                      </div>
                    </button>

                    {expanded && (
                      <div className="mx-3 mb-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                        <dl className="grid gap-3 text-sm sm:grid-cols-2">
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
                              Build time
                            </dt>
                            <dd className="mt-1 font-mono text-ink-200">
                              {formatDuration(lead.deployDurationSec)}
                            </dd>
                            <p className="mt-0.5 text-[10px] text-ink-600">
                              DeepSeek copy + deploy + sheet update
                            </p>
                          </div>
                          <div>
                            <dt className="text-xs font-medium uppercase tracking-wide text-ink-500">
                              Est. AI cost
                            </dt>
                            <dd className="mt-1 font-mono text-ink-200">
                              {formatUsd(costPerSiteUsd)}
                            </dd>
                            <p className="mt-0.5 text-[10px] text-ink-600">
                              ~{tokensPerSite.toLocaleString()} tokens · env estimate, no API call
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
          )}
        </div>

        {liveLeads.length > 0 && (
          <div className="border-t border-white/[0.06] px-5 py-3 text-xs text-ink-500">
            Build times recorded on deploy · cost uses{" "}
            <span className="font-mono text-ink-400">DEEPSEEK_EST_COST_PER_SITE</span> (no extra AI
            calls)
          </div>
        )}
      </div>
    </div>
  );
}

export function liveSiteCount(leads: Lead[]) {
  return leads.filter((lead) => lead.liveUrl?.trim().startsWith("http")).length;
}
