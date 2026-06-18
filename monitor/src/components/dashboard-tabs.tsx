"use client";

export type DashboardTab = "overview" | "leads" | "sites" | "runs" | "markets" | "ai";

type TabDef = {
  id: DashboardTab;
  label: string;
  badge?: number;
};

export function DashboardTabs({
  active,
  onChange,
  tabs,
}: {
  active: DashboardTab;
  onChange: (tab: DashboardTab) => void;
  tabs: TabDef[];
}) {
  return (
    <nav
      className="-mx-1 overflow-x-auto px-1 pb-0.5"
      aria-label="Dashboard sections"
    >
      <div className="flex min-w-max gap-1 rounded-xl border border-white/[0.08] bg-ink-900/50 p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition sm:px-4 ${
              active === tab.id
                ? "bg-signal-blue text-ink-950 shadow-sm"
                : "text-ink-400 hover:bg-white/5 hover:text-ink-200"
            }`}
          >
            {tab.label}
            {tab.badge != null && tab.badge > 0 && (
              <span
                className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold leading-none ${
                  active === tab.id
                    ? "bg-ink-950/20 text-ink-950"
                    : "bg-white/10 text-ink-300"
                }`}
              >
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>
    </nav>
  );
}
