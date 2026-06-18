import type { AiCostStats, PipelineStats } from "@/lib/types";
import { AiCostPanel } from "./ai-cost-panel";
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

export function AiDashboard({
  aiCost,
  stats,
}: {
  aiCost: AiCostStats;
  stats: PipelineStats;
}) {
  const affordable = aiCost.sitesAffordable;
  const estTokensLeft =
    affordable !== null ? affordable * aiCost.tokensPerSite : null;

  const pendingDeploy = stats.readyToDeploy;
  const budgetCoversPending =
    affordable !== null && pendingDeploy > 0
      ? affordable >= pendingDeploy
      : null;

  return (
    <div className="space-y-6">
      <Panel
        title="Build capacity"
        subtitle="How many more customer sites your DeepSeek balance can fund"
      >
        <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
          <div className="rounded-2xl border border-signal-green/25 bg-gradient-to-br from-signal-green/10 to-transparent p-6 md:p-8">
            <p className="stat-label text-signal-green">Sites you can still build</p>
            <p className="mt-3 text-5xl font-bold tracking-tight text-ink-50 md:text-6xl">
              {affordable !== null ? `~${affordable.toLocaleString()}` : "—"}
            </p>
            <p className="mt-4 max-w-md text-sm text-ink-300">
              {affordable !== null ? (
                <>
                  At <span className="font-mono text-ink-100">${aiCost.costPerSiteUsd.toFixed(2)}</span>{" "}
                  per site (est.), your{" "}
                  <span className="font-semibold text-signal-green">{money(aiCost.balanceUsd)}</span>{" "}
                  balance covers about{" "}
                  <span className="font-semibold">{affordable}</span> more DeepSeek copy + site
                  generations.
                </>
              ) : (
                "Connect DEEPSEEK_API_KEY on Vercel to see live balance and capacity."
              )}
            </p>
            {estTokensLeft !== null && (
              <p className="mt-2 text-xs text-ink-500">
                ≈ {tokens(estTokensLeft)} tokens at ~{aiCost.tokensPerSite.toLocaleString()}/site
              </p>
            )}
          </div>

          <div className="space-y-3">
            <div className="rounded-xl border border-white/[0.06] bg-ink-900/40 p-4">
              <p className="stat-label">Formula</p>
              <p className="mt-2 font-mono text-sm text-ink-200">
                floor(balance ÷ ${aiCost.costPerSiteUsd.toFixed(2)})
              </p>
              {aiCost.balanceUsd !== null && affordable !== null && (
                <p className="mt-1 font-mono text-xs text-ink-500">
                  floor({aiCost.balanceUsd.toFixed(2)} ÷ {aiCost.costPerSiteUsd}) = {affordable}
                </p>
              )}
            </div>

            <div className="rounded-xl border border-white/[0.06] bg-ink-900/40 p-4">
              <p className="stat-label">Queue vs budget</p>
              <p className="mt-2 text-sm text-ink-200">
                <span className="font-semibold text-signal-amber">{pendingDeploy}</span> leads ready
                to deploy (copy done, no live URL)
              </p>
              {budgetCoversPending === true && (
                <p className="mt-2 text-xs text-signal-green">
                  Balance covers the full pending queue.
                </p>
              )}
              {budgetCoversPending === false && affordable !== null && (
                <p className="mt-2 text-xs text-signal-amber">
                  Budget covers {affordable} of {pendingDeploy} pending — top up or run in smaller
                  batches.
                </p>
              )}
              {pendingDeploy === 0 && (
                <p className="mt-2 text-xs text-ink-500">No leads waiting for deploy right now.</p>
              )}
            </div>

            <div className="rounded-xl border border-white/[0.06] bg-ink-900/40 p-4">
              <p className="stat-label">Already built (est. spend)</p>
              <p className="mt-2 text-lg font-semibold text-ink-100">
                {money(aiCost.estimatedSpendUsd)}
              </p>
              <p className="mt-1 text-xs text-ink-500">
                {aiCost.sitesWithCopy} sites × ${aiCost.costPerSiteUsd.toFixed(2)}
              </p>
            </div>
          </div>
        </div>

        {aiCost.isAvailable === false && (
          <p className="mt-4 rounded-lg border border-signal-red/30 bg-signal-red/10 px-4 py-3 text-sm text-signal-red">
            DeepSeek reports insufficient balance — top up before the next pipeline run.
          </p>
        )}
      </Panel>

      <AiCostPanel aiCost={aiCost} />

      <Panel title="Cost assumptions" subtitle="Tune via Vercel env vars">
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div className="rounded-lg bg-ink-900/40 px-4 py-3">
            <dt className="text-ink-500">DEEPSEEK_EST_COST_PER_SITE</dt>
            <dd className="mt-1 font-mono text-ink-100">${aiCost.costPerSiteUsd.toFixed(2)}</dd>
          </div>
          <div className="rounded-lg bg-ink-900/40 px-4 py-3">
            <dt className="text-ink-500">DEEPSEEK_EST_TOKENS_PER_SITE</dt>
            <dd className="mt-1 font-mono text-ink-100">{aiCost.tokensPerSite.toLocaleString()}</dd>
          </div>
        </dl>
        <p className="mt-4 text-xs text-ink-600">
          GitHub Actions and kem-llc Pages are free for public repos. Only DeepSeek copy generation
          is metered here. Adjust estimates if your niches produce longer pages.
        </p>
      </Panel>
    </div>
  );
}
