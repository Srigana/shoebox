// Usage tracker for the Trailmark analytics server: where visitors come from and whether they go
// on to upload and export. Events go to /collect on this site, which next.config.ts forwards to
// the analytics server, so the browser only talks to Shoebox.
//
// Turned off unless both COLLECTOR_URL and NEXT_PUBLIC_COLLECTOR_WRITE_KEY are set (next.config.ts
// clears the key when the URL is missing, so the two can never disagree). When NEXT_PUBLIC_GA_MEASUREMENT_ID is
// set, the same upload and export events also go to Google Analytics for comparison.

import { getClientId } from "./api.ts";

const ENDPOINT = "/collect/batch";
const DELETE_ENDPOINT = "/collect/delete";
const WRITE_KEY = process.env.NEXT_PUBLIC_COLLECTOR_WRITE_KEY ?? "";
const OUTBOX_KEY = "shoebox.outbox";
const OUTBOX_LIMIT = 50;
/** Matches the server's MAX_EVENT_AGE_HOURS default; older events would be rejected anyway. */
const OUTBOX_MAX_AGE_MS = 72 * 3600 * 1000;

export const trackingEnabled = WRITE_KEY !== "";

export type Attribution = {
  referrer_host?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
};

export type TrackEvent =
  | { name: "visit" }
  | { name: "upload"; properties: { sample: boolean; file_type: "image" | "pdf" } }
  | { name: "upload_failed"; properties: { sample: boolean; error: string } }
  | { name: "export"; properties: { format: "quickbooks" | "full"; rows: number; real_rows: number } };

type WireEvent = {
  event_id: string;
  name: TrackEvent["name"];
  anonymous_id: string;
  timestamp: string;
  context: Attribution & { page_path: string };
  properties?: Record<string, unknown>;
};

const UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign"] as const;

/**
 * Reads campaign tags from the landing URL and the referring site's hostname. Only the hostname of
 * the referrer is kept, never its path or query, so search terms and private links are not recorded.
 * Links from Shoebox itself are not a referral.
 */
export function attributionFrom(href: string, referrer: string): Attribution {
  const out: Attribution = {};
  let page: URL;
  try {
    page = new URL(href);
  } catch {
    return out;
  }
  for (const key of UTM_KEYS) {
    const value = page.searchParams.get(key)?.trim();
    if (value) out[key] = value.slice(0, 200);
  }
  if (referrer) {
    const host = referrerHost(referrer);
    if (host && host !== page.hostname.toLowerCase() && /^[a-z0-9.-]+$/.test(host)) out.referrer_host = host;
  }
  return out;
}

/** The hostname of a referrer URL, or "" when there is none or it cannot be parsed. */
export function referrerHost(referrer: string): string {
  try {
    return referrer ? new URL(referrer).hostname.toLowerCase().slice(0, 253) : "";
  } catch {
    return "";
  }
}

// Used when local storage is blocked, so those visitors are not all merged under one "anon" ID.
let pageOnlyId: string | null = null;

function anonymousId(): string {
  const id = getClientId();
  if (id !== "anon") return id;
  pageOnlyId ??= crypto.randomUUID();
  return pageOnlyId;
}

function readOutbox(): WireEvent[] {
  try {
    const saved = JSON.parse(localStorage.getItem(OUTBOX_KEY) ?? "[]");
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function writeOutbox(events: WireEvent[]): void {
  try {
    const fresh = events.filter((e) => Date.now() - Date.parse(e.timestamp) < OUTBOX_MAX_AGE_MS).slice(-OUTBOX_LIMIT);
    if (fresh.length) localStorage.setItem(OUTBOX_KEY, JSON.stringify(fresh));
    else localStorage.removeItem(OUTBOX_KEY);
  } catch {
    /* storage blocked or full: the events are lost, which is acceptable for analytics */
  }
}

async function send(events: WireEvent[]): Promise<void> {
  try {
    const res = await fetch(ENDPOINT, {
      method: "POST",
      keepalive: true,
      headers: { "Content-Type": "application/json", "X-Write-Key": WRITE_KEY },
      body: JSON.stringify({ events }),
    });
    // Server unavailable or rate limited: keep the events and retry on the next visit.
    // Every event has a unique event_id, so a retry is never counted twice.
    if (res.status >= 500 || res.status === 429) writeOutbox([...readOutbox(), ...events]);
  } catch {
    writeOutbox([...readOutbox(), ...events]);
  }
}

type Gtag = (command: "event", name: string, params?: Record<string, unknown>) => void;

function sendToGoogleAnalytics(event: TrackEvent): void {
  // GA records page views by itself; only the actions are sent.
  if (event.name === "visit") return;
  const gtag = (window as unknown as { gtag?: Gtag }).gtag;
  if (typeof gtag === "function") gtag("event", event.name, event.properties);
}

export function track(event: TrackEvent, attribution: Attribution = {}): void {
  if (typeof window === "undefined") return;
  sendToGoogleAnalytics(event);
  if (!trackingEnabled) return;
  const wire: WireEvent = {
    event_id: crypto.randomUUID(),
    name: event.name,
    anonymous_id: anonymousId(),
    timestamp: new Date().toISOString(),
    context: { page_path: window.location.pathname.slice(0, 1024), ...(event.name === "visit" ? attribution : {}) },
  };
  if ("properties" in event) wire.properties = event.properties;
  void send([wire]);
}

/** Records the landing visit with its source, and retries anything left from an earlier visit. */
export function trackVisit(): void {
  if (typeof window === "undefined" || !trackingEnabled) return;
  const pending = readOutbox();
  if (pending.length) {
    writeOutbox([]);
    void send(pending);
  }
  track({ name: "visit" }, attributionFrom(window.location.href, document.referrer));
}

/** Deletes everything the analytics server holds for this browser's ID. */
export async function deleteTrackedData(id: string): Promise<void> {
  if (!trackingEnabled) return;
  const res = await fetch(DELETE_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Write-Key": WRITE_KEY },
    body: JSON.stringify({ anonymous_id: id }),
  });
  if (!res.ok) throw new Error(String(res.status));
  try {
    localStorage.removeItem(OUTBOX_KEY);
  } catch {
    /* nothing to clear */
  }
}

export function fileType(file: File): "image" | "pdf" {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf") ? "pdf" : "image";
}
