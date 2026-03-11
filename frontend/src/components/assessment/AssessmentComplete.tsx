"use client";

import { ProficiencyScore } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ArrowRight, CheckCircle } from "lucide-react";
import { motion } from "motion/react";

interface AssessmentCompleteProps {
  scores: ProficiencyScore[];
  onContinue: () => void;
}

export function AssessmentComplete({
  scores,
  onContinue,
}: AssessmentCompleteProps) {
  const avgScore = Math.round(
    scores.reduce((sum, s) => sum + s.score, 0) / scores.length
  );

  return (
    <motion.div
      className="mx-auto max-w-lg space-y-6 p-6"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <div className="text-center space-y-2">
        <CheckCircle className="mx-auto h-12 w-12 text-cyan" />
        <h2 className="font-heading text-2xl font-bold">
          Assessment Complete
        </h2>
        <p className="text-muted-foreground">
          Average proficiency: <span className="text-cyan font-semibold">{avgScore}%</span>
        </p>
      </div>

      <div className="space-y-3">
        {scores.map((score, i) => (
          <motion.div
            key={score.skillId}
            className="rounded-lg border border-border bg-card p-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">{score.skillName}</span>
              <span className="text-sm font-mono text-cyan">{score.score}%</span>
            </div>
            <Progress value={score.score} className="h-2" />
            <p className="mt-1 text-xs text-muted-foreground">
              {score.reasoning}
            </p>
          </motion.div>
        ))}
      </div>

      <Button
        onClick={onContinue}
        className="w-full bg-cyan text-background hover:bg-cyan/90 font-semibold gap-2"
      >
        View Gap Analysis
        <ArrowRight className="h-4 w-4" />
      </Button>
    </motion.div>
  );
}
