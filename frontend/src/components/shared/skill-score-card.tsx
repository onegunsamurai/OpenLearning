"use client";

import { ProficiencyScore } from "@/lib/types";
import { Progress } from "@/components/ui/progress";
import { motion } from "motion/react";

interface SkillScoreCardProps {
  score: ProficiencyScore;
  index: number;
  showReasoning?: boolean;
}

export function SkillScoreCard({
  score,
  index,
  showReasoning = true,
}: SkillScoreCardProps) {
  return (
    <motion.div
      className="rounded-lg border border-border bg-card p-3"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index * 0.1, 0.4) }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">{score.skillName}</span>
        <span className="text-sm font-mono text-cyan">{score.score}%</span>
      </div>
      <Progress
        value={score.score}
        className="h-2"
        aria-label={`${score.skillName} proficiency: ${score.score}%`}
      />
      {showReasoning && (
        <p className="mt-1 text-xs text-muted-foreground">{score.reasoning}</p>
      )}
    </motion.div>
  );
}
