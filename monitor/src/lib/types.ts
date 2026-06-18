export type Lead = {
  name: string;
  niche: string;
  phone: string;
  city: string;
  scrapedStatus: string;
  copyStatus: string;
  liveUrl: string;
  mapsUrl: string;
  /** Per-site deploy job duration (generate + deploy + sheet), seconds */
  deployDurationSec: number | null;
};

export type PipelineStats = {
  total: number;
  scraped: number;
  copyDone: number;
  copyPending: number;
  liveSites: number;
  readyToDeploy: number;
};

export type NicheCount = { niche: string; count: number };
export type CityCount = { city: string; count: number };

export type WorkflowRun = {
  id: number;
  name: string;
  status: "queued" | "in_progress" | "completed" | "failure" | "cancelled" | string;
  conclusion: string | null;
  niche: string | null;
  city: string | null;
  runMode: "all_niches" | "single" | "pending" | "unknown";
  maxResults: number | null;
  createdAt: string;
  updatedAt: string;
  durationSec: number | null;
  htmlUrl: string;
};

export type AiCostStats = {
  configured: boolean;
  balanceUsd: number | null;
  grantedUsd: number | null;
  toppedUpUsd: number | null;
  isAvailable: boolean | null;
  sitesWithCopy: number;
  estimatedTokens: number;
  estimatedSpendUsd: number;
  costPerSiteUsd: number;
  tokensPerSite: number;
  /** How many more sites DeepSeek balance can cover at est. cost/site */
  sitesAffordable: number | null;
  error: string | null;
};

export type MarketNiche = { id: string; label: string; search_term: string };
export type MarketCity = {
  id: string;
  label: string;
  phase: number;
  search_term: string;
};

export type MarketsConfig = {
  default_niche: string;
  default_city: string;
  niches: MarketNiche[];
  cities: MarketCity[];
  expansion_notes: string;
};

export type MarketCoverage = {
  nicheId: string;
  nicheLabel: string;
  cityId: string;
  cityLabel: string;
  phase: number;
  leadCount: number;
  liveCount: number;
  lastRunAt: string | null;
  lastRunStatus: string | null;
};

export type DashboardData = {
  fetchedAt: string;
  stats: PipelineStats;
  leads: Lead[];
  byNiche: NicheCount[];
  byCity: CityCount[];
  runs: WorkflowRun[];
  runSummary: {
    total: number;
    success: number;
    failure: number;
    lastSuccessAt: string | null;
    lastFailureAt: string | null;
    successRate: number;
  };
  markets: MarketsConfig;
  coverage: MarketCoverage[];
  aiCost: AiCostStats;
  links: {
    sheets: string | null;
    actions: string | null;
    repo: string | null;
    kemOrg: string | null;
  };
  errors: string[];
};
