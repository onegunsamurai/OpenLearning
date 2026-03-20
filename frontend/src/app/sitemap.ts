import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = "https://openlearning.dev";

  return [
    { url: baseUrl, changeFrequency: "weekly", priority: 1.0 },
    { url: `${baseUrl}/assess`, changeFrequency: "weekly", priority: 0.8 },
    {
      url: `${baseUrl}/gap-analysis`,
      changeFrequency: "weekly",
      priority: 0.7,
    },
    {
      url: `${baseUrl}/learning-plan`,
      changeFrequency: "weekly",
      priority: 0.7,
    },
    { url: `${baseUrl}/demo`, changeFrequency: "monthly", priority: 0.6 },
    {
      url: `${baseUrl}/demo/assess`,
      changeFrequency: "monthly",
      priority: 0.5,
    },
    {
      url: `${baseUrl}/demo/report`,
      changeFrequency: "monthly",
      priority: 0.5,
    },
  ];
}
