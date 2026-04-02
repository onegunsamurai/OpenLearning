"use client";

import type { AssessmentReportResponse } from "@/lib/api";
import type { ParsedMaterial } from "@/lib/materials";
import { ConceptCard } from "./ConceptCard";
import { motion } from "motion/react";

type PipelinePlan = AssessmentReportResponse["learningPlan"];
type PipelinePhase = PipelinePlan["phases"][number];

interface PlanTimelineProps {
  plan: PipelinePlan;
  activePhase: number;
  materialsByConceptId?: Map<string, ParsedMaterial>;
  materialsLoading?: boolean;
}

export function PlanTimeline({ plan, activePhase, materialsByConceptId, materialsLoading }: PlanTimelineProps) {
  const phase: PipelinePhase | undefined = plan.phases.find(
    (p) => p.phaseNumber === activePhase
  );
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
          Phase {phase.phaseNumber}: {phase.title}
        </h3>
        <p className="text-sm text-muted-foreground">{phase.rationale}</p>
      </div>
      <div className="space-y-3">
        {phase.concepts.map((concept, i) => (
          <ConceptCard
            key={concept}
            concept={concept}
            resources={phase.resources}
            index={i}
            material={materialsByConceptId?.get(concept)}
            materialsLoading={materialsLoading}
          />
        ))}
      </div>
    </motion.div>
  );
}
