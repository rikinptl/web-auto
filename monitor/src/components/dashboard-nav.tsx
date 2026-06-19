"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { liveSiteCount } from "@/components/live-sites-panel";
import { useDashboard } from "@/components/dashboard-provider";

const ROUTES = [
  { href: "/overview", label: "Overview" },
  { href: "/leads", label: "Leads", badgeKey: "leads" as const },
  { href: "/sites", label: "Live sites", badgeKey: "sites" as const },
  { href: "/runs", label: "Runs", badgeKey: "runs" as const },
  { href: "/markets", label: "Markets", badgeKey: "markets" as const },
  { href: "/ai", label: "AI & budget" },
];

export function DashboardNav() {
  const pathname = usePathname();
  const { data } = useDashboard();

  const badges = {
    leads: data?.stats.total ?? 0,
    sites: data ? liveSiteCount(data.leads) : 0,
    runs: data?.runs.length ?? 0,
    markets: data ? data.markets.niches.length * data.markets.cities.length : 0,
  };

  return (
    <nav className="border-b border-white/[0.06] bg-ink-950/95" aria-label="Dashboard sections">
      <div className="mx-auto max-w-[1400px] overflow-x-auto px-4 md:px-6">
        <ul className="flex min-w-max gap-0">
          {ROUTES.map((tab) => {
            const active = pathname === tab.href || pathname.startsWith(`${tab.href}/`);
            const badge =
              tab.badgeKey != null ? badges[tab.badgeKey] : undefined;

            return (
              <li key={tab.href}>
                <Link
                  href={tab.href}
                  className={`relative flex items-center gap-2 border-b-2 px-4 py-3.5 text-sm font-medium transition ${
                    active
                      ? "border-signal-blue text-signal-blue"
                      : "border-transparent text-ink-400 hover:border-white/20 hover:text-ink-200"
                  }`}
                >
                  {tab.label}
                  {badge != null && badge > 0 && (
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold leading-none ${
                        active ? "bg-signal-blue/20 text-signal-blue" : "bg-white/10 text-ink-400"
                      }`}
                    >
                      {badge}
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}
