"use client";

import { GapItem } from "@/lib/types";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { motion } from "motion/react";

const priorityColors: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  low: "bg-green-500/20 text-green-400 border-green-500/30",
};

interface GapCardProps {
  gap: GapItem;
  index: number;
}

export function GapCard({ gap, index }: GapCardProps) {
  return (
    <motion.div
      className="rounded-xl border border-border bg-card p-4 space-y-3"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
    >
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-sm">{gap.skillName}</h4>
        <Badge
          variant="outline"
          className={cn("text-xs capitalize", priorityColors[gap.priority])}
        >
          {gap.priority}
        </Badge>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Current: {gap.currentLevel}%</span>
          <span>Target: {gap.targetLevel}%</span>
        </div>
        <div className="relative">
          <Progress value={gap.targetLevel} className="h-2 opacity-30" />
          <div className="absolute inset-0">
            <Progress value={gap.currentLevel} className="h-2" />
          </div>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">{gap.recommendation}</p>
    </motion.div>
  );
}
