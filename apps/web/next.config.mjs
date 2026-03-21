import path from "node:path";
import { fileURLToPath } from "node:url";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(__dirname, "../..");

/**
 * Keep dev and production build artifacts in separate directories so
 * `next dev` and `next build` cannot corrupt each other's chunk graph.
 */
const nextConfig = (phase) => ({
  reactStrictMode: true,
  poweredByHeader: false,
  distDir: phase === PHASE_DEVELOPMENT_SERVER ? ".next-dev" : ".next-prod",
  outputFileTracingRoot: repoRoot,
});

export default nextConfig;
