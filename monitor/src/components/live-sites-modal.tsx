"use client";

import { useEffect, useMemo } from "react";
import type { Lead } from "@/lib/types";

export function LiveSitesModal({
  leads,
  open,
  onClose,
  orgName = "kem-llc",
}: {
  leads: Lead[];
  open: boolean;
  onClose: () => void;
  orgName?: string;
}) {
  const liveLeads = useMemo(
    () =>
      leads
        .filter((lead) => lead.liveUrl?.trim().startsWith("http"))
        .sort((a, b) => a.name.localeCompare(b.name)),
    [leads]
  );

  useEffect(() => {
    if (!open) return;
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
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[10vh]">
      <button
        type="button"
        aria-label="Close"
        className="absolute inset-0 bg-ink-950/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-labelledby="live-sites-title"
        className="panel relative z-10 flex max-h-[min(70vh,640px)] w-full max-w-2xl flex-col shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] p-5">
          <div>
            <h2 id="live-sites-title" className="text-lg font-semibold text-ink-100">
              {orgName} live sites
            </h2>
            <p className="mt-1 text-sm text-ink-400">
              {liveLeads.length} deployed · click a row to open the customer site
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
            <ul className="divide-y divide-white/[0.04]">
              {liveLeads.map((lead) => (
                <li key={`${lead.name}-${lead.phone}`}>
                  <a
                    href={lead.liveUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="flex flex-col gap-1 rounded-xl px-3 py-3 transition hover:bg-white/[0.04] sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-ink-100">{lead.name}</p>
                      <p className="text-xs text-ink-500">
                        {lead.niche || "—"}
                        {lead.city ? ` · ${lead.city}` : ""}
                      </p>
                    </div>
                    <span className="truncate font-mono text-xs text-signal-green sm:max-w-[50%] sm:text-right">
                      {lead.liveUrl.replace(/^https?:\/\//, "")}
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>

        {liveLeads.length > 0 && (
          <div className="border-t border-white/[0.06] px-5 py-3 text-xs text-ink-500">
            Pattern:{" "}
            <span className="font-mono text-ink-400">https://{orgName}.github.io/&#123;slug&#125;/</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function liveSiteCount(leads: Lead[]) {
  return leads.filter((lead) => lead.liveUrl?.trim().startsWith("http")).length;
}
