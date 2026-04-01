"use client";

import { ProficiencyScore } from "@/lib/types";
import { GapSummary } from "@/components/gap-analysis/GapSummary";
import { SkillScoreCard } from "@/components/shared/skill-score-card";
import { Button } from "@/components/ui/button";
import { isMaxLevel } from "@/lib/constants";
import { ArrowRight, Trophy, Plus } from "lucide-react";
import { motion } from "motion/react";

interface NoGapsHeroProps {
  scores: ProficiencyScore[];
  overallReadiness: number;
  summary: string;
  targetLevel: string;
  onStartOver: () => void;
  onContinue: () => void;
}

export function NoGapsHero({
  scores,
  overallReadiness,
  summary,
  targetLevel,
  onStartOver,
  onContinue,
}: NoGapsHeroProps) {
  const atMaxLevel = isMaxLevel(targetLevel);

  return (
    <div className="space-y-8">
      {/* Hero section */}
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
          Outstanding Performance!
        </h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          You demonstrated strong proficiency across all assessed skills. No
          learning gaps were identified.
        </p>
      </motion.div>

      {/* Readiness ring */}
      <GapSummary readiness={overallReadiness} summary={summary} />

      {/* Skill scores */}
      {scores.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-heading text-lg font-semibold text-center">
            Your Skill Scores
          </h3>
          {scores.map((score, i) => (
            <SkillScoreCard key={score.skillId} score={score} index={i} />
          ))}
        </div>
      )}

      {/* CTAs */}
      <div className="flex flex-col items-center gap-3 pb-8 sm:flex-row sm:justify-center">
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
          onClick={onContinue}
          size="lg"
          variant="outline"
          className="gap-2 border-border"
        >
          View Learning Plan
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
