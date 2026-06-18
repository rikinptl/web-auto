import type { WorkflowRun } from "./types";

const SINGLE_RE = /Scrape \+ deploy (.+) in (.+)/i;
const PARALLEL_RE = /Parallel scrape \((\d+) max\) in (.+)/i;
const PENDING_RE = /^Deploy pending leads$/i;

function parseRunName(name: string): Pick<WorkflowRun, "niche" | "city" | "runMode" | "maxResults"> {
  const pending = name.match(PENDING_RE);
  if (pending) {
    return { niche: null, city: null, runMode: "pending", maxResults: null };
  }

  const parallel = name.match(PARALLEL_RE);
  if (parallel) {
    return {
      niche: "all niches",
      city: parallel[2].replace(/_/g, " "),
      runMode: "all_niches",
      maxResults: Number.parseInt(parallel[1], 10) || null,
    };
  }

  const single = name.match(SINGLE_RE);
  if (single) {
    return {
      niche: single[1].replace(/_/g, " "),
      city: single[2].replace(/_/g, " "),
      runMode: "single",
      maxResults: null,
    };
  }

  return { niche: null, city: null, runMode: "unknown", maxResults: null };
}

function durationSec(start: string, end: string | null): number | null {
  if (!end) return null;
  const ms = new Date(end).getTime() - new Date(start).getTime();
  return Math.max(0, Math.round(ms / 1000));
}

type GhRun = {
  id: number;
  name: string;
  status: string;
  conclusion: string | null;
  created_at: string;
  updated_at: string;
  html_url: string;
};

export async function fetchWorkflowRuns(limit = 40): Promise<WorkflowRun[]> {
  const token = process.env.GITHUB_TOKEN;
  const repo = process.env.GITHUB_REPO || "rikinptl/web-auto";
  if (!token) {
    throw new Error("GITHUB_TOKEN is not set");
  }

  const url = `https://api.github.com/repos/${repo}/actions/workflows/deploy.yml/runs?per_page=${limit}`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    next: { revalidate: 60 },
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GitHub API ${res.status}: ${body.slice(0, 200)}`);
  }

  const data = (await res.json()) as { workflow_runs: GhRun[] };
  return data.workflow_runs.map((run) => {
    const parsed = parseRunName(run.name);
    return {
      id: run.id,
      name: run.name,
      status: run.status,
      conclusion: run.conclusion,
      createdAt: run.created_at,
      updatedAt: run.updated_at,
      durationSec: durationSec(run.created_at, run.updated_at),
      htmlUrl: run.html_url,
      ...parsed,
    };
  });
}
