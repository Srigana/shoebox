import type { ParseResponse } from "./types.ts";

export type EventName = "visit" | "correction" | "export_csv" | "export_qbo" | "feedback";

export function getClientId(): string {
  try {
    let id = localStorage.getItem("shoebox.cid");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("shoebox.cid", id);
    }
    return id;
  } catch {
    return "anon";
  }
}

export async function parseReceipt(blob: Blob, name: string): Promise<ParseResponse> {
  const body = new FormData();
  body.append("file", blob, name);
  const res = await fetch("/api/parse", { method: "POST", body, headers: { "X-Client-Id": getClientId() } });
  if (!res.ok) {
    let msg = `Upload failed (${res.status}).`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") msg = j.detail;
    } catch {
      /* non-JSON error */
    }
    throw new Error(msg);
  }
  return res.json();
}

export function logEvent(event: EventName, meta: Record<string, unknown> = {}): void {
  fetch("/api/events", {
    method: "POST",
    keepalive: true,
    headers: { "Content-Type": "application/json", "X-Client-Id": getClientId() },
    body: JSON.stringify({ event, meta }),
  }).catch(() => {});
}
