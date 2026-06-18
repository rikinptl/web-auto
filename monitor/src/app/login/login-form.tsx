"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginForm() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const params = useSearchParams();
  const from = params.get("from") || "/";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const res = await fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    setLoading(false);
    if (!res.ok) {
      setError("Wrong password");
      return;
    }
    router.push(from);
    router.refresh();
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={onSubmit} className="panel w-full max-w-md p-8">
        <p className="stat-label mb-2">Web Auto</p>
        <h1 className="mb-2 text-2xl font-semibold">Founder Monitor</h1>
        <p className="mb-8 text-sm text-ink-400">Enter your dashboard password to continue.</p>
        <label className="mb-2 block text-sm text-ink-300">Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-4 w-full rounded-xl border border-white/10 bg-ink-800 px-4 py-3 text-ink-100 outline-none ring-signal-blue/40 focus:ring-2"
          autoFocus
        />
        {error && <p className="mb-4 text-sm text-signal-red">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-signal-blue px-4 py-3 font-medium text-ink-950 transition hover:brightness-110 disabled:opacity-60"
        >
          {loading ? "Signing in…" : "Open dashboard"}
        </button>
      </form>
    </main>
  );
}
