import { readFile } from "fs/promises";
import path from "path";
import type { MarketsConfig } from "./types";

export async function loadMarketsConfig(): Promise<MarketsConfig> {
  const candidates = [
    path.join(process.cwd(), "src/data/markets.json"),
    path.join(process.cwd(), "../config/markets.json"),
    path.join(process.cwd(), "../../config/markets.json"),
  ];

  for (const file of candidates) {
    try {
      const raw = await readFile(file, "utf-8");
      return JSON.parse(raw) as MarketsConfig;
    } catch {
      continue;
    }
  }

  throw new Error("markets.json not found");
}
