"use client";

import { LearningModule } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { BookOpen, HelpCircle, Wrench, Clock } from "lucide-react";
import { motion } from "motion/react";

const typeConfig = {
  theory: {
    icon: BookOpen,
    color: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    label: "Theory",
  },
  quiz: {
    icon: HelpCircle,
    color: "bg-purple-500/20 text-purple-400 border-purple-500/30",
    label: "Quiz",
  },
  lab: {
    icon: Wrench,
    color: "bg-green-500/20 text-green-400 border-green-500/30",
    label: "Lab",
  },
};

interface ModuleCardProps {
  module: LearningModule;
  index: number;
}

export function ModuleCard({ module, index }: ModuleCardProps) {
  const config = typeConfig[module.type];
  const Icon = config.icon;

  return (
    <motion.div
      className="rounded-xl border border-border bg-card p-4 space-y-3"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border bg-secondary">
            <Icon className="h-4 w-4 text-muted-foreground" />
          </div>
          <div>
            <h4 className="font-medium text-sm">{module.title}</h4>
            <p className="text-xs text-muted-foreground mt-0.5">
              {module.description}
            </p>
          </div>
        </div>
        <Badge
          variant="outline"
          className={cn("text-xs shrink-0", config.color)}
        >
          {config.label}
        </Badge>
      </div>

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Clock className="h-3.5 w-3.5" />
        {module.durationHours}h
      </div>

      {module.objectives.length > 0 && (
        <ul className="space-y-1">
          {module.objectives.map((obj, i) => (
            <li key={i} className="text-xs text-muted-foreground flex gap-2">
              <span className="text-cyan shrink-0">-</span>
              {obj}
            </li>
          ))}
        </ul>
      )}

      {module.resources.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {module.resources.map((res, i) => (
            <span
              key={i}
              className="inline-block rounded bg-secondary px-2 py-0.5 text-xs text-muted-foreground"
            >
              {res}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  );
}
