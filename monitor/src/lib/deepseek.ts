import type { AiCostStats } from "./types";

const BALANCE_URL = "https://api.deepseek.com/user/balance";

type BalanceResponse = {
  is_available: boolean;
  balance_infos: {
    currency: string;
    total_balance: string;
    granted_balance: string;
    topped_up_balance: string;
  }[];
};

function parseUsdAmount(value: string | undefined): number | null {
  if (!value) return null;
  const n = Number.parseFloat(value);
  return Number.isFinite(n) ? n : null;
}

function pickUsdBalance(info: BalanceResponse["balance_infos"]) {
  const usd =
    info.find((row) => row.currency.toUpperCase() === "USD") ??
    info.find((row) => row.currency.toUpperCase() === "CNY") ??
    info[0];
  if (!usd) return { total: null, granted: null, toppedUp: null };
  return {
    total: parseUsdAmount(usd.total_balance),
    granted: parseUsdAmount(usd.granted_balance),
    toppedUp: parseUsdAmount(usd.topped_up_balance),
  };
}

export async function fetchDeepSeekBalance(): Promise<{
  isAvailable: boolean;
  totalUsd: number | null;
  grantedUsd: number | null;
  toppedUpUsd: number | null;
} | null> {
  const apiKey = process.env.DEEPSEEK_API_KEY;
  if (!apiKey) return null;

  const res = await fetch(BALANCE_URL, {
    headers: {
      Authorization: `Bearer ${apiKey}`,
      Accept: "application/json",
    },
    next: { revalidate: 120 },
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`DeepSeek balance API ${res.status}: ${body.slice(0, 160)}`);
  }

  const data = (await res.json()) as BalanceResponse;
  const balances = pickUsdBalance(data.balance_infos);
  return {
    isAvailable: data.is_available,
    totalUsd: balances.total,
    grantedUsd: balances.granted,
    toppedUpUsd: balances.toppedUp,
  };
}

export function estimateAiUsage(copyDone: number): Pick<
  AiCostStats,
  | "sitesWithCopy"
  | "estimatedTokens"
  | "estimatedSpendUsd"
  | "costPerSiteUsd"
  | "tokensPerSite"
  | "sitesAffordable"
> {
  const costPerSiteUsd = Number.parseFloat(process.env.DEEPSEEK_EST_COST_PER_SITE ?? "0.03");
  const tokensPerSite = Number.parseInt(process.env.DEEPSEEK_EST_TOKENS_PER_SITE ?? "4500", 10);
  const safeCost = Number.isFinite(costPerSiteUsd) && costPerSiteUsd > 0 ? costPerSiteUsd : 0.03;
  const safeTokens = Number.isFinite(tokensPerSite) ? tokensPerSite : 4500;

  return {
    sitesWithCopy: copyDone,
    estimatedTokens: copyDone * safeTokens,
    estimatedSpendUsd: Math.round(copyDone * safeCost * 100) / 100,
    costPerSiteUsd: safeCost,
    tokensPerSite: safeTokens,
    sitesAffordable: null,
  };
}

function affordableSites(balanceUsd: number | null, costPerSiteUsd: number): number | null {
  if (balanceUsd === null || costPerSiteUsd <= 0) return null;
  return Math.floor(balanceUsd / costPerSiteUsd);
}

export async function buildAiCostStats(copyDone: number): Promise<AiCostStats> {
  const estimate = estimateAiUsage(copyDone);
  const configured = Boolean(process.env.DEEPSEEK_API_KEY);

  if (!configured) {
    return {
      configured: false,
      balanceUsd: null,
      grantedUsd: null,
      toppedUpUsd: null,
      isAvailable: null,
      error: "Set DEEPSEEK_API_KEY on Vercel to show live balance",
      ...estimate,
    };
  }

  try {
    const balance = await fetchDeepSeekBalance();
    if (!balance) {
      return {
        configured: false,
        balanceUsd: null,
        grantedUsd: null,
        toppedUpUsd: null,
        isAvailable: null,
        error: null,
        ...estimate,
      };
    }

    return {
      configured: true,
      balanceUsd: balance.totalUsd,
      grantedUsd: balance.grantedUsd,
      toppedUpUsd: balance.toppedUpUsd,
      isAvailable: balance.isAvailable,
      error: null,
      ...estimate,
      sitesAffordable: affordableSites(balance.totalUsd, estimate.costPerSiteUsd),
    };
  } catch (e) {
    return {
      configured: true,
      balanceUsd: null,
      grantedUsd: null,
      toppedUpUsd: null,
      isAvailable: null,
      error: e instanceof Error ? e.message : "Failed to load DeepSeek balance",
      ...estimate,
    };
  }
}
