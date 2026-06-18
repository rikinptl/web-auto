import type { AiCostStats } from "@/lib/types";
import { Panel } from "./ui";

function money(value: number | null) {
  if (value === null) return "—";
  return `$${value.toFixed(2)}`;
}

function tokens(value: number) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return String(value);
}

export function AiCostPanel({ aiCost }: { aiCost: AiCostStats }) {
  const remainingAfterEstimate =
    aiCost.balanceUsd !== null
      ? Math.max(0, aiCost.balanceUsd - aiCost.estimatedSpendUsd)
      : null;

  return (
    <Panel
      title="AI usage & cost"
      subtitle="DeepSeek copy generation — balance from API, usage estimated from sheet"
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-white/[0.06] bg-ink-900/40 p-4">
          <p className="stat-label">Account balance</p>
          <p className="mt-2 text-2xl font-semibold text-signal-green">{money(aiCost.balanceUsd)}</p>
          <p className="mt-1 text-xs text-ink-500">
            {aiCost.configured
              ? aiCost.isAvailable === false
                ? "Low balance — top up at platform.deepseek.com"
                : `Paid ${money(aiCost.toppedUpUsd)} · Granted ${money(aiCost.grantedUsd)}`
              : "Add DEEPSEEK_API_KEY on Vercel"}
          </p>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-ink-900/40 p-4">
          <p className="stat-label">Sites with AI copy</p>
          <p className="mt-2 text-2xl font-semibold text-signal-violet">{aiCost.sitesWithCopy}</p>
          <p className="mt-1 text-xs text-ink-500">Rows with copy status Done</p>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-ink-900/40 p-4">
          <p className="stat-label">Est. tokens used</p>
          <p className="mt-2 text-2xl font-semibold text-ink-100">~{tokens(aiCost.estimatedTokens)}</p>
          <p className="mt-1 text-xs text-ink-500">~4,500 tokens/site assumed</p>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-ink-900/40 p-4">
          <p className="stat-label">Est. pipeline spend</p>
          <p className="mt-2 text-2xl font-semibold text-signal-amber">{money(aiCost.estimatedSpendUsd)}</p>
          <p className="mt-1 text-xs text-ink-500">
            {aiCost.sitesWithCopy} × ${aiCost.costPerSiteUsd.toFixed(2)}/site
            {remainingAfterEstimate !== null && (
              <> · ~{money(remainingAfterEstimate)} left after est.</>
            )}
          </p>
        </div>
      </div>

      {aiCost.error && (
        <p className="mt-4 text-sm text-signal-amber">{aiCost.error}</p>
      )}

      <p className="mt-4 text-xs text-ink-600">
        Token counts are estimated (~4.5k tokens/site). Live balance from{" "}
        <a
          href="https://api-docs.deepseek.com/api/get-user-balance"
          target="_blank"
          rel="noreferrer"
          className="text-signal-blue hover:underline"
        >
          DeepSeek /user/balance
        </a>
        . Per-run token logging can be added to the pipeline later for exact numbers.
      </p>
    </Panel>
  );
}
