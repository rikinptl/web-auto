"use client";

import { useDashboard } from "@/components/dashboard-provider";
import { LiveSitesPanel } from "@/components/live-sites-panel";
import { Panel } from "@/components/ui";

export default function SitesPage() {
  const { data } = useDashboard();
  if (!data) return null;

  const orgName = data.links.kemOrg?.split("/").pop() ?? "kem-llc";

  return (
    <Panel title={`${orgName} live sites`} subtitle="Per-business links, timing, and cost">
      <LiveSitesPanel
        leads={data.leads}
        orgName={orgName}
        costPerSiteUsd={data.aiCost.costPerSiteUsd}
        tokensPerSite={data.aiCost.tokensPerSite}
      />
    </Panel>
  );
}
