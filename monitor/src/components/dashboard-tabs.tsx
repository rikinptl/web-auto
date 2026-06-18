"use client";

type Tab = "pipeline" | "ai";

export function DashboardTabs({
  active,
  onChange,
}: {
  active: Tab;
  onChange: (tab: Tab) => void;
}) {
  const tabs: { id: Tab; label: string }[] = [
    { id: "pipeline", label: "Pipeline" },
    { id: "ai", label: "AI & budget" },
  ];

  return (
    <nav
      className="flex gap-1 rounded-xl border border-white/[0.08] bg-ink-900/50 p-1"
      aria-label="Dashboard sections"
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            active === tab.id
              ? "bg-signal-blue text-ink-950 shadow-sm"
              : "text-ink-400 hover:bg-white/5 hover:text-ink-200"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}

export type DashboardTab = Tab;
