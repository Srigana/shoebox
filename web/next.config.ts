import type { NextConfig } from "next";

// In production, /api/* is proxied to the Python service on Render, so the browser
// only ever talks to one origin (no CORS, no exposed backend URL).
const API_URL = process.env.API_URL ?? "http://localhost:8000";
// The Trailmark analytics server. /collect/* is forwarded to its /v1/* routes when this is set.
const COLLECTOR_URL = (process.env.COLLECTOR_URL ?? "").replace(/\/+$/, "");
const COLLECTOR_WRITE_KEY = process.env.NEXT_PUBLIC_COLLECTOR_WRITE_KEY ?? "";
if (COLLECTOR_WRITE_KEY && !COLLECTOR_URL) {
  console.warn("NEXT_PUBLIC_COLLECTOR_WRITE_KEY is set but COLLECTOR_URL is not: usage tracking stays off.");
}

const config: NextConfig = {
  // Tracking needs both values. Clearing the key here keeps the tracker (and the delete call
  // on the privacy page) off unless /collect is actually proxied somewhere.
  env: { NEXT_PUBLIC_COLLECTOR_WRITE_KEY: COLLECTOR_URL ? COLLECTOR_WRITE_KEY : "" },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_URL}/api/:path*` },
      ...(COLLECTOR_URL ? [{ source: "/collect/:path*", destination: `${COLLECTOR_URL}/v1/:path*` }] : []),
    ];
  },
};

export default config;
