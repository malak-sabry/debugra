import type { NextConfig } from "next";

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  transpilePackages: ["@debugra/schemas"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${ORCHESTRATOR_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
