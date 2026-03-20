import robots from "./robots";

describe("robots", () => {
  const result = robots();

  it("allows all user agents at /", () => {
    const rules = Array.isArray(result.rules) ? result.rules : [result.rules];
    const wildcardRule = rules.find((r) => r.userAgent === "*");
    expect(wildcardRule).toBeDefined();
    expect(wildcardRule!.allow).toBe("/");
  });

  it("disallows /api/ and /export/", () => {
    const rules = Array.isArray(result.rules) ? result.rules : [result.rules];
    const wildcardRule = rules.find((r) => r.userAgent === "*");
    expect(wildcardRule!.disallow).toContain("/api/");
    expect(wildcardRule!.disallow).toContain("/export/");
  });

  it("includes sitemap URL", () => {
    expect(result.sitemap).toBe("https://openlearning.dev/sitemap.xml");
  });
});
