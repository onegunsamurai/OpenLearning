import { LEVELS, MAX_LEVEL, LEVEL_LABELS, isMaxLevel } from "./constants";

describe("constants", () => {
  it("MAX_LEVEL is the last element of LEVELS", () => {
    expect(MAX_LEVEL).toBe(LEVELS[LEVELS.length - 1]);
  });

  it("LEVEL_LABELS has an entry for every level", () => {
    for (const level of LEVELS) {
      expect(LEVEL_LABELS[level]).toBeDefined();
    }
  });

  describe("isMaxLevel", () => {
    it("returns true for staff", () => {
      expect(isMaxLevel("staff")).toBe(true);
    });

    it("returns false for other levels", () => {
      expect(isMaxLevel("junior")).toBe(false);
      expect(isMaxLevel("mid")).toBe(false);
      expect(isMaxLevel("senior")).toBe(false);
    });

    it("returns false for undefined", () => {
      expect(isMaxLevel(undefined)).toBe(false);
    });

    it("returns false for unknown strings", () => {
      expect(isMaxLevel("expert")).toBe(false);
    });
  });
});
