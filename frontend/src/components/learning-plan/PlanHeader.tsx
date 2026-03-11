"use client";

import { LearningPlan } from "@/lib/types";
import { BookOpen, Clock, Calendar, Target } from "lucide-react";
import { motion } from "motion/react";

interface PlanHeaderProps {
  plan: LearningPlan;
}

export function PlanHeader({ plan }: PlanHeaderProps) {
  const totalModules = plan.phases.reduce(
    (sum, p) => sum + p.modules.length,
    0
  );
  const totalSkills = [
    ...new Set(plan.phases.flatMap((p) => p.modules.flatMap((m) => m.skillIds))),
  ].length;

  const stats = [
    { icon: BookOpen, label: "Modules", value: totalModules },
    { icon: Clock, label: "Hours", value: plan.totalHours },
    { icon: Calendar, label: "Weeks", value: plan.totalWeeks },
    { icon: Target, label: "Skills", value: totalSkills },
  ];

  return (
    <div className="space-y-4">
      <h2 className="font-heading text-2xl font-bold">{plan.title}</h2>
      <p className="text-sm text-muted-foreground">{plan.summary}</p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            className="rounded-lg border border-border bg-card p-3 text-center"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <stat.icon className="mx-auto h-5 w-5 text-cyan mb-1" />
            <div className="text-xl font-heading font-bold">{stat.value}</div>
            <div className="text-xs text-muted-foreground">{stat.label}</div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
