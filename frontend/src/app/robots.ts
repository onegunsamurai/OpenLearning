import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/export/"],
      },
    ],
    sitemap: "https://openlearning.dev/sitemap.xml",
  };
}
