// Simulation runner client. The Monte-Carlo runner now lives inside the legal-os
// backend under /api/simulation (single backend on 8080). SSE events are streamed
// from this base; the /runs endpoints are ungated (auth is deferred).
export const SIM_API_BASE =
  (process.env.NEXT_PUBLIC_LEGAL_OS_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8080") + "/api/simulation";
