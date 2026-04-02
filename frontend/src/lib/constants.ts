export const LEVELS = ["junior", "mid", "senior", "staff"] as const;

export type Level = (typeof LEVELS)[number];

export const MAX_LEVEL: Level = LEVELS[LEVELS.length - 1];

export const LEVEL_LABELS: Record<Level, string> = {
  junior: "Junior",
  mid: "Mid",
  senior: "Senior",
  staff: "Staff",
};

export function isMaxLevel(level: string | undefined): boolean {
  return level === MAX_LEVEL;
}

export const QUALITY_THRESHOLDS = {
  high: 0.8,
  acceptable: 0.6,
} as const;

export const QUALITY_LABELS = {
  high: {
    text: "High Quality",
    color: "bg-green-500/20 text-green-300 border-green-500/30",
  },
  acceptable: {
    text: "Acceptable",
    color: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  },
  low: {
    text: "Needs Review",
    color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  },
  flagged: {
    text: "Review Suggested",
    color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  },
} as const;

export const MATERIALS_POLL_INTERVAL_MS = 3000;
export const MATERIALS_MAX_RETRIES = 6;
