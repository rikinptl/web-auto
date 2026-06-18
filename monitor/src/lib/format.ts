export function formatDuration(sec: number | null | undefined): string {
  if (sec == null || !Number.isFinite(sec) || sec <= 0) return "—";
  const total = Math.round(sec);
  if (total < 60) return `${total}s`;
  const m = Math.floor(total / 60);
  const s = total % 60;
  if (m < 60) return s > 0 ? `${m}m ${s}s` : `${m}m`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return rm > 0 ? `${h}h ${rm}m` : `${h}h`;
}

export function formatUsd(amount: number): string {
  if (amount < 0.01) return "<$0.01";
  return `$${amount.toFixed(2)}`;
}

export function leadKey(lead: { name: string; phone: string }) {
  return `${lead.name}::${lead.phone}`;
}
