import type { NextConfig } from "next";

// In production, /api/* is proxied to the Python service on Render, so the browser
// only ever talks to one origin (no CORS, no exposed backend URL).
const API_URL = process.env.API_URL ?? "http://localhost:8000";

const config: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default config;
