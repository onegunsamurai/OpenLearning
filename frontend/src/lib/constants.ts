export const LEVELS = ["junior", "mid", "senior", "staff"] as const;

export type Level = (typeof LEVELS)[number];

export const MAX_LEVEL: Level = "staff";

export const LEVEL_LABELS: Record<Level, string> = {
  junior: "Junior",
  mid: "Mid",
  senior: "Senior",
  staff: "Staff",
};

export function isMaxLevel(level: string | undefined): boolean {
  return level === MAX_LEVEL;
}
