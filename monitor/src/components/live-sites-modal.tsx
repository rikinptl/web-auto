"use client";

import { useEffect } from "react";
import type { Lead } from "@/lib/types";
import { LiveSitesPanel } from "@/components/live-sites-panel";

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
          <h2 id="live-sites-title" className="text-lg font-semibold text-ink-100">
            {orgName} live sites
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-ink-300 hover:bg-white/5"
          >
            Close
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          <LiveSitesPanel
            leads={leads}
            orgName={orgName}
            costPerSiteUsd={costPerSiteUsd}
            tokensPerSite={tokensPerSite}
          />
        </div>
      </div>
    </div>
  );
}

export { liveSiteCount } from "@/components/live-sites-panel";
