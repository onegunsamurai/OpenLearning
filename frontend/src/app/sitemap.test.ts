import sitemap from "./sitemap";

describe("sitemap", () => {
  const entries = sitemap();
  const urls = entries.map((e) => e.url);

  it("includes all 7 public routes", () => {
    expect(entries).toHaveLength(7);
    expect(urls).toContain("https://openlearning.dev");
    expect(urls).toContain("https://openlearning.dev/assess");
    expect(urls).toContain("https://openlearning.dev/gap-analysis");
    expect(urls).toContain("https://openlearning.dev/learning-plan");
    expect(urls).toContain("https://openlearning.dev/demo");
    expect(urls).toContain("https://openlearning.dev/demo/assess");
    expect(urls).toContain("https://openlearning.dev/demo/report");
  });

  it("excludes /export routes", () => {
    const exportUrls = urls.filter((u) => u.includes("/export"));
    expect(exportUrls).toHaveLength(0);
  });

  it("sets homepage priority to 1.0", () => {
    const homepage = entries.find((e) => e.url === "https://openlearning.dev");
    expect(homepage!.priority).toBe(1.0);
  });
});
