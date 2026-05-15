import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: ["@whatwg-node/fetch", "graphql-yoga"],
};

export default nextConfig;
