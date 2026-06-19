import { google } from "googleapis";
import type { Lead } from "./types";

const HEADERS = [
  "Business Name",
  "Niche",
  "Phone",
  "City",
  "Scraped Status",
  "DeepSeek Copy Status",
  "Live URL",
  "Google Maps URL",
  "Deploy Sec",
  "Site Created",
  "Rating",
  "Reviews",
] as const;

function parseReviews(raw: string | undefined): number | null {
  if (!raw?.trim()) return null;
  const n = Number.parseInt(raw.trim(), 10);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

function parseRating(raw: string | undefined): number | null {
  if (!raw?.trim()) return null;
  const n = Number.parseFloat(raw.trim());
  return Number.isFinite(n) && n > 0 ? n : null;
}

function parseDeploySec(raw: string | undefined): number | null {
  if (!raw?.trim()) return null;
  const n = Number.parseInt(raw.trim(), 10);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function getAuth() {
  const raw = process.env.GOOGLE_SERVICE_ACCOUNT_JSON;
  if (!raw) {
    throw new Error("GOOGLE_SERVICE_ACCOUNT_JSON is not set");
  }
  const credentials = JSON.parse(raw);
  return new google.auth.GoogleAuth({
    credentials,
    scopes: ["https://www.googleapis.com/auth/spreadsheets.readonly"],
  });
}

function rowToLead(row: string[]): Lead | null {
  if (!row[0]?.trim()) return null;
  return {
    name: row[0] || "",
    niche: row[1] || "",
    phone: row[2] || "",
    city: row[3] || "",
    scrapedStatus: row[4] || "",
    copyStatus: row[5] || "",
    liveUrl: row[6] || "",
    mapsUrl: row[7] || "",
    deployDurationSec: parseDeploySec(row[8]),
    siteCreatedAt: row[9]?.trim() || null,
    rating: parseRating(row[10]),
    reviews: parseReviews(row[11]),
  };
}

export async function fetchLeadsFromSheet(): Promise<Lead[]> {
  const spreadsheetId = process.env.GOOGLE_SHEETS_SPREADSHEET_ID;
  if (!spreadsheetId) {
    throw new Error("GOOGLE_SHEETS_SPREADSHEET_ID is not set");
  }

  const auth = getAuth();
  const sheets = google.sheets({ version: "v4", auth });
  const range = `Sheet1!A1:L1000`;

  const res = await sheets.spreadsheets.values.get({ spreadsheetId, range });
  const rows = res.data.values ?? [];
  if (rows.length <= 1) return [];

  const header = rows[0];
  if (header.join("|") !== HEADERS.join("|")) {
    // tolerate minor header drift — map by position
  }

  return rows.slice(1).map(rowToLead).filter((l): l is Lead => l !== null);
}
