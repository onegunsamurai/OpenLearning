"use client";

import { LearningPlan } from "@/lib/types";
import { ModuleCard } from "./ModuleCard";
import { motion } from "motion/react";

interface PlanTimelineProps {
  plan: LearningPlan;
  activePhase: number;
}

export function PlanTimeline({ plan, activePhase }: PlanTimelineProps) {
  const phase = plan.phases.find((p) => p.phase === activePhase);
  if (!phase) return null;

  return (
    <motion.div
      key={activePhase}
      className="space-y-4"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="space-y-1">
        <h3 className="font-heading text-lg font-semibold">
          Phase {phase.phase}: {phase.name}
        </h3>
        <p className="text-sm text-muted-foreground">{phase.description}</p>
      </div>
      <div className="space-y-3">
        {phase.modules.map((mod, i) => (
          <ModuleCard key={mod.id} module={mod} index={i} />
        ))}
      </div>
    </motion.div>
  );
}
