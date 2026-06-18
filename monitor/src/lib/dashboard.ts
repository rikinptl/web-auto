import { fetchWorkflowRuns } from "./github";
import { buildAiCostStats } from "./deepseek";
import { loadMarketsConfig } from "./markets";
import { fetchLeadsFromSheet } from "./sheets";
import type {
  CityCount,
  DashboardData,
  Lead,
  MarketCoverage,
  NicheCount,
  PipelineStats,
} from "./types";

function isDone(value: string) {
  return value.trim().toLowerCase() === "done";
}

function hasLiveUrl(url: string) {
  return Boolean(url?.trim() && url.startsWith("http"));
}

function computeStats(leads: Lead[]): PipelineStats {
  const copyDone = leads.filter((l) => isDone(l.copyStatus)).length;
  const liveSites = leads.filter((l) => hasLiveUrl(l.liveUrl)).length;
  return {
    total: leads.length,
    scraped: leads.filter((l) => isDone(l.scrapedStatus)).length,
    copyDone,
    copyPending: leads.length - copyDone,
    liveSites,
    readyToDeploy: leads.filter((l) => isDone(l.copyStatus) && !hasLiveUrl(l.liveUrl)).length,
  };
}

function countBy<T extends string>(items: Lead[], pick: (l: Lead) => T): { key: T; count: number }[] {
  const map = new Map<T, number>();
  for (const item of items) {
    const key = pick(item);
    if (!key) continue;
    map.set(key, (map.get(key) ?? 0) + 1);
  }
  return [...map.entries()]
    .map(([key, count]) => ({ key, count }))
    .sort((a, b) => b.count - a.count);
}

function normalize(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function buildCoverage(
  markets: Awaited<ReturnType<typeof loadMarketsConfig>>,
  leads: Lead[],
  runs: Awaited<ReturnType<typeof fetchWorkflowRuns>>
): MarketCoverage[] {
  const rows: MarketCoverage[] = [];

  for (const niche of markets.niches) {
    for (const city of markets.cities) {
      const nicheNorm = normalize(niche.label);
      const cityNorm = normalize(city.label);

      const matchingLeads = leads.filter((l) => {
        const ln = normalize(l.niche);
        const lc = normalize(l.city);
        return (
          (ln.includes(normalize(niche.search_term)) || ln.includes(nicheNorm)) &&
          (lc.includes(normalize(city.search_term)) || lc.includes(cityNorm))
        );
      });

      const matchingRuns = runs.filter((r) => {
        if (r.runMode === "all_niches") {
          return (
            normalize(r.city ?? "").includes(normalize(city.search_term)) ||
            normalize(r.city ?? "").includes(normalize(city.label))
          );
        }
        if (!r.niche || !r.city) return false;
        return (
          (normalize(r.niche).includes(normalize(niche.id.replace(/_/g, " "))) ||
            normalize(r.niche).includes(normalize(niche.label))) &&
          (normalize(r.city).includes(normalize(city.id.replace(/_/g, " "))) ||
            normalize(r.city).includes(normalize(city.label)))
        );
      });

      const lastRun = matchingRuns[0] ?? null;

      rows.push({
        nicheId: niche.id,
        nicheLabel: niche.label,
        cityId: city.id,
        cityLabel: city.label,
        phase: city.phase,
        leadCount: matchingLeads.length,
        liveCount: matchingLeads.filter((l) => hasLiveUrl(l.liveUrl)).length,
        lastRunAt: lastRun?.createdAt ?? null,
        lastRunStatus: lastRun?.conclusion ?? lastRun?.status ?? null,
      });
    }
  }

  return rows;
}

export async function getDashboardData(): Promise<DashboardData> {
  const errors: string[] = [];
  let leads: Lead[] = [];
  let runs: Awaited<ReturnType<typeof fetchWorkflowRuns>> = [];
  let markets = {
    default_niche: "plumber",
    default_city: "dallas",
    niches: [],
    cities: [],
    expansion_notes: "",
  } as Awaited<ReturnType<typeof loadMarketsConfig>>;

  try {
    leads = await fetchLeadsFromSheet();
  } catch (e) {
    errors.push(e instanceof Error ? e.message : "Failed to load Google Sheet");
  }

  try {
    runs = await fetchWorkflowRuns(40);
  } catch (e) {
    errors.push(e instanceof Error ? e.message : "Failed to load GitHub Actions runs");
  }

  try {
    markets = await loadMarketsConfig();
  } catch (e) {
    errors.push(e instanceof Error ? e.message : "Failed to load markets config");
  }

  const stats = computeStats(leads);
  const byNiche: NicheCount[] = countBy(leads, (l) => l.niche).map(({ key, count }) => ({
    niche: key,
    count,
  }));
  const byCity: CityCount[] = countBy(leads, (l) => l.city).map(({ key, count }) => ({
    city: key,
    count,
  }));

  const completed = runs.filter((r) => r.status === "completed");
  const success = completed.filter((r) => r.conclusion === "success");
  const failure = completed.filter((r) => r.conclusion === "failure");

  const repo = process.env.GITHUB_REPO || "rikinptl/web-auto";
  const deployOrg = process.env.DEPLOY_ORG || "kem-llc";
  const aiCost = await buildAiCostStats(stats.copyDone);

  return {
    fetchedAt: new Date().toISOString(),
    stats,
    leads,
    byNiche,
    byCity,
    runs,
    runSummary: {
      total: runs.length,
      success: success.length,
      failure: failure.length,
      lastSuccessAt: success[0]?.createdAt ?? null,
      lastFailureAt: failure[0]?.createdAt ?? null,
      successRate: completed.length ? Math.round((success.length / completed.length) * 100) : 0,
    },
    markets,
    coverage: buildCoverage(markets, leads, runs),
    aiCost,
    links: {
      sheets: process.env.GOOGLE_SHEETS_URL ?? null,
      actions:
        process.env.GITHUB_ACTIONS_URL ??
        `https://github.com/${repo}/actions/workflows/deploy.yml`,
      repo: `https://github.com/${repo}`,
      kemOrg: `https://github.com/${deployOrg}`,
    },
    errors,
  };
}
