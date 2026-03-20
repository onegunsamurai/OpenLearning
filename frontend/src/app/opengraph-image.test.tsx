import { alt, size, contentType } from "./opengraph-image";

describe("opengraph-image", () => {
  it("exports correct size (1200x630)", () => {
    expect(size).toEqual({ width: 1200, height: 630 });
  });

  it("exports png content type", () => {
    expect(contentType).toBe("image/png");
  });

  it("exports alt text", () => {
    expect(alt).toBe("OpenLearning — AI-Powered Learning Engineer");
  });
});
