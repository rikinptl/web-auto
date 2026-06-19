"use client";

import { useMemo, useState } from "react";
import type { Lead } from "@/lib/types";
import { ExternalLink, Panel, StatusBadge, statusKind } from "./ui";

export function LeadsTable({ leads }: { leads: Lead[] }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "live" | "pending" | "ready">("all");

  const filtered = useMemo(() => {
    return leads.filter((lead) => {
      const q = query.toLowerCase();
      const matchesQuery =
        !q ||
        lead.name.toLowerCase().includes(q) ||
        lead.niche.toLowerCase().includes(q) ||
        lead.city.toLowerCase().includes(q) ||
        lead.phone.includes(q);

      const isLive = Boolean(lead.liveUrl?.startsWith("http"));
      const copyDone = lead.copyStatus.toLowerCase() === "done";

      const matchesFilter =
        filter === "all" ||
        (filter === "live" && isLive) ||
        (filter === "pending" && !copyDone) ||
        (filter === "ready" && copyDone && !isLive);

      return matchesQuery && matchesFilter;
    });
  }, [leads, query, filter]);

  return (
    <Panel
      title="Lead inventory"
      subtitle={`${filtered.length} of ${leads.length} businesses`}
      action={
        <div className="flex flex-wrap gap-2">
          {(["all", "live", "ready", "pending"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                filter === f
                  ? "bg-signal-blue/20 text-signal-blue"
                  : "bg-white/5 text-ink-400 hover:text-ink-200"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      }
    >
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search name, niche, city, phone…"
        className="mb-4 w-full rounded-xl border border-white/10 bg-ink-800 px-4 py-2.5 text-sm text-ink-100 outline-none focus:ring-2 focus:ring-signal-blue/30"
      />

      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] border-collapse">
          <thead>
            <tr className="border-b border-white/10">
              <th className="table-head pb-3 pr-4">Business</th>
              <th className="table-head pb-3 pr-4">Niche</th>
              <th className="table-head pb-3 pr-4">City</th>
              <th className="table-head pb-3 pr-4">Phone</th>
              <th className="table-head pb-3 pr-4">Reviews</th>
              <th className="table-head pb-3 pr-4">Scraped</th>
              <th className="table-head pb-3 pr-4">Copy</th>
              <th className="table-head pb-3">Links</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-sm text-ink-500">
                  No leads match your filters. Run the GitHub Actions pipeline to populate the sheet.
                </td>
              </tr>
            ) : (
              filtered.map((lead) => (
                <tr key={`${lead.name}-${lead.phone}`} className="border-b border-white/[0.04]">
                  <td className="table-cell pr-4 font-medium text-ink-100">{lead.name}</td>
                  <td className="table-cell pr-4">{lead.niche || "—"}</td>
                  <td className="table-cell pr-4">{lead.city || "—"}</td>
                  <td className="table-cell pr-4 font-mono text-xs">{lead.phone || "—"}</td>
                  <td className="table-cell pr-4 text-xs text-ink-300">
                    {lead.reviews != null ? (
                      <>
                        {lead.rating != null && (
                          <span className="text-signal-amber">{lead.rating}★ </span>
                        )}
                        {lead.reviews.toLocaleString()}
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="table-cell pr-4">
                    <StatusBadge
                      value={lead.scrapedStatus || "—"}
                      kind={statusKind(lead.scrapedStatus, "scraped")}
                    />
                  </td>
                  <td className="table-cell pr-4">
                    <StatusBadge
                      value={lead.copyStatus || "—"}
                      kind={statusKind(lead.copyStatus, "copy")}
                    />
                  </td>
                  <td className="table-cell">
                    <div className="flex flex-wrap gap-3 text-xs">
                      {lead.mapsUrl ? (
                        <ExternalLink href={lead.mapsUrl}>Maps</ExternalLink>
                      ) : (
                        <span className="text-ink-600">Maps</span>
                      )}
                      {lead.liveUrl ? (
                        <ExternalLink href={lead.liveUrl}>Live site</ExternalLink>
                      ) : (
                        <span className="text-ink-600">No site</span>
                      )}
                    </div>
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
