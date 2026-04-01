// ============================================================
// API Contracts for Issue #144: Success State UI
// TypeScript interfaces for new/modified components.
// ============================================================

import type { ProficiencyScore } from "@/lib/types";

// --- D6: Shared constants (frontend/src/lib/constants.ts) ---

export const LEVELS = ["junior", "mid", "senior", "staff"] as const;
export type Level = (typeof LEVELS)[number];
export const MAX_LEVEL: Level = "staff";
export const LEVEL_LABELS: Record<Level, string> = {
  junior: "Junior",
  mid: "Mid",
  senior: "Senior",
  staff: "Staff",
};

// --- D2: SkillScoreCard ---

export interface SkillScoreCardProps {
  score: ProficiencyScore;
  index: number;
  showReasoning?: boolean; // default true
}

// --- D3: NoGapsHero (gap-analysis page) ---

export interface NoGapsHeroProps {
  scores: ProficiencyScore[];
  overallReadiness: number;
  summary: string;
  targetLevel: string;
  sessionId: string;
  onStartOver: () => void;
  onContinue: () => void;
}

// --- D4: NoGapsSuccess (learning-plan page) ---

export interface NoGapsSuccessProps {
  scores: ProficiencyScore[];
  targetLevel: string;
  onStartOver: () => void;
  sessionId?: string | null;
}
