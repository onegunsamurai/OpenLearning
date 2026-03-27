"use client";

import { useState } from "react";
import Link from "next/link";
import type { UserAssessmentSummary } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { motion } from "motion/react";
import { Clock, Target, ArrowRight, Play, RotateCcw, Trash2 } from "lucide-react";

const statusConfig: Record<
  string,
  { label: string; color: string }
> = {
  active: {
    label: "In Progress",
    color: "bg-cyan/20 text-cyan border-cyan/30",
  },
  completed: {
    label: "Completed",
    color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  },
  timed_out: {
    label: "Timed Out",
    color: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  },
  error: {
    label: "Error",
    color: "bg-red-500/20 text-red-400 border-red-500/30",
  },
};

interface AssessmentCardProps {
  session: UserAssessmentSummary;
  index: number;
  onDelete?: (sessionId: string) => Promise<void>;
}

export function AssessmentCard({ session, index, onDelete }: AssessmentCardProps) {
  const config = statusConfig[session.status] ?? statusConfig.active;
  const date = new Date(session.createdAt).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!onDelete) return;
    setDeleting(true);
    try {
      await onDelete(session.sessionId);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <motion.div
      className="rounded-xl border border-border bg-card p-5 space-y-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          {session.roleName && (
            <p className="text-sm font-medium">{session.roleName}</p>
          )}
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={cn("text-xs", config.color)}
            >
              {config.label}
            </Badge>
            <span className="text-xs text-muted-foreground capitalize">
              {session.targetLevel}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">{date}</p>
        </div>

        {session.status === "completed" &&
          session.overallReadiness != null && (
            <div className="text-right">
              <div className="text-2xl font-heading font-bold text-cyan">
                {session.overallReadiness}%
              </div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
                Readiness
              </div>
            </div>
          )}
      </div>

      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <Target className="h-3.5 w-3.5" />
          {session.skillCount} skill{session.skillCount !== 1 ? "s" : ""}
        </span>
        {session.status === "completed" && session.completedAt && (
          <span className="flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" />
            Completed{" "}
            {new Date(session.completedAt).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            })}
          </span>
        )}
      </div>

      <div className="flex gap-2">
        {session.status === "completed" && (
          <Button asChild size="sm" className="bg-cyan text-background hover:bg-cyan/90 gap-1.5">
            <Link href={`/gap-analysis?session=${session.sessionId}`}>
              View Results
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        )}
        {session.status === "active" && (
          <Button asChild size="sm" className="bg-cyan text-background hover:bg-cyan/90 gap-1.5">
            <Link href={`/assess?session=${session.sessionId}`}>
              Resume
              <Play className="h-3.5 w-3.5" />
            </Link>
          </Button>
        )}
        {(session.status === "timed_out" || session.status === "error") && (
          <Button asChild size="sm" variant="outline" className="gap-1.5">
            <Link href="/">
              Start New
              <RotateCcw className="h-3.5 w-3.5" />
            </Link>
          </Button>
        )}
        {onDelete && (
          <Button
            size="sm"
            variant="ghost"
            className="text-muted-foreground hover:text-red-400 gap-1.5 ml-auto"
            onClick={handleDelete}
            disabled={deleting}
            aria-label="Delete assessment"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </motion.div>
  );
}
