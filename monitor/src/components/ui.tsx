import type { ReactNode } from "react";

export function StatusBadge({
  value,
  kind = "neutral",
}: {
  value: string;
  kind?: "success" | "warning" | "danger" | "neutral" | "info";
}) {
  const styles = {
    success: "bg-signal-green/15 text-signal-green border-signal-green/30",
    warning: "bg-signal-amber/15 text-signal-amber border-signal-amber/30",
    danger: "bg-signal-red/15 text-signal-red border-signal-red/30",
    info: "bg-signal-blue/15 text-signal-blue border-signal-blue/30",
    neutral: "bg-white/5 text-ink-300 border-white/10",
  }[kind];

  return (
    <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${styles}`}>
      {value || "—"}
    </span>
  );
}

export function statusKind(
  status: string | null,
  field: "scraped" | "copy" | "run" = "run"
): "success" | "warning" | "danger" | "neutral" | "info" {
  const s = (status || "").toLowerCase();
  if (field === "run") {
    if (s === "success") return "success";
    if (s === "failure") return "danger";
    if (s === "in_progress" || s === "queued") return "info";
    return "neutral";
  }
  if (s === "done") return "success";
  if (s === "pending") return "warning";
  return "neutral";
}

export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel p-5 md:p-6 ${className}`}>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-ink-100">{title}</h2>
          {subtitle && <p className="mt-1 text-sm text-ink-400">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function ExternalLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-signal-blue hover:underline"
    >
      {children}
    </a>
  );
}

export function formatRelative(iso: string | null) {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  return `${days}d ago`;
}

export function formatDuration(sec: number | null) {
  if (sec == null) return "—";
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}m ${s}s`;
}
