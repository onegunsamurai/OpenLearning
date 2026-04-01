"use client";

import { ProficiencyScore } from "@/lib/types";
import { SkillScoreCard } from "@/components/shared/skill-score-card";
import { Button } from "@/components/ui/button";
import { isMaxLevel, LEVEL_LABELS, type Level } from "@/lib/constants";
import { ArrowRight, Trophy, Plus, RotateCcw } from "lucide-react";
import { motion } from "motion/react";

interface NoGapsSuccessProps {
  scores: ProficiencyScore[];
  targetLevel: string;
  onStartOver: () => void;
}

export function NoGapsSuccess({
  scores,
  targetLevel,
  onStartOver,
}: NoGapsSuccessProps) {
  const atMaxLevel = isMaxLevel(targetLevel);
  const levelLabel =
    LEVEL_LABELS[targetLevel as Level] ?? targetLevel;

  return (
    <div className="mx-auto max-w-2xl space-y-8 py-8">
      {/* Hero */}
      <motion.div
        className="text-center space-y-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", delay: 0.2 }}
        >
          <Trophy aria-hidden="true" className="mx-auto h-16 w-16 text-yellow-400" />
        </motion.div>
        <h2 className="font-heading text-2xl font-bold">
          No Learning Plan Needed!
        </h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          You&apos;ve demonstrated mastery at the {levelLabel} level. All skills
          met or exceeded the target proficiency — there are no gaps to address.
        </p>
      </motion.div>

      {/* Skill scores */}
      {scores.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-heading text-lg font-semibold text-center">
            Skills Verified
          </h3>
          <div className="grid gap-2">
            {scores.map((score, i) => (
              <SkillScoreCard
                key={score.skillId}
                score={score}
                index={i}
                showReasoning={false}
              />
            ))}
          </div>
          <p className="text-center text-sm text-muted-foreground">
            {scores.length} {scores.length === 1 ? "skill" : "skills"} verified
          </p>
        </div>
      )}

      {/* CTAs */}
      <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
        <Button
          onClick={onStartOver}
          size="lg"
          className="bg-cyan text-background hover:bg-cyan/90 font-semibold gap-2"
        >
          {atMaxLevel ? (
            <>
              <Plus className="h-4 w-4" />
              Add More Skills
            </>
          ) : (
            <>
              <ArrowRight className="h-4 w-4" />
              Try a Harder Level
            </>
          )}
        </Button>
        <Button
          onClick={onStartOver}
          size="lg"
          variant="outline"
          className="gap-2 border-border text-muted-foreground"
        >
          <RotateCcw className="h-4 w-4" />
          Start New Assessment
        </Button>
      </div>
    </div>
  );
}
