import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // React Compiler disabled in dev — its Babel worker pool was spawning a
  // runaway swarm of node processes that exhausted RAM. Kept on for prod builds.
  reactCompiler: process.env.NODE_ENV === "production",
};

export default nextConfig;
