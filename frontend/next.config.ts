import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

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
      source: "/api/:path*",
      destination: `${backendUrl}/api/:path*`,
    },
  ],
};

export default nextConfig;
