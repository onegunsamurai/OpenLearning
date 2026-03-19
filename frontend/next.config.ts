import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "avatars.githubusercontent.com",
      },
    ],
  },
  rewrites: async () => [
    {
      source: "/api/auth/:path*",
      destination: "http://localhost:8000/api/auth/:path*",
    },
  ],
};

export default nextConfig;
