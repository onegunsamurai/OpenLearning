"use client";

import type { AssessmentReportResponse } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { BookOpen, Video, Wrench, FileText, ExternalLink } from "lucide-react";
import { motion } from "motion/react";

type PipelineResource = AssessmentReportResponse["learningPlan"]["phases"][number]["resources"][number];

const typeIcons: Record<string, typeof BookOpen> = {
  video: Video,
  article: FileText,
  project: Wrench,
  exercise: Wrench,
};

const typeColors: Record<string, string> = {
  video: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  article: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  project: "bg-green-500/20 text-green-400 border-green-500/30",
  exercise: "bg-orange-500/20 text-orange-400 border-orange-500/30",
};

interface ConceptCardProps {
  concept: string;
  resources: PipelineResource[];
  index: number;
}

export function ConceptCard({ concept, resources, index }: ConceptCardProps) {
  return (
    <motion.div
      className="rounded-xl border border-border bg-card p-4 space-y-3"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border bg-secondary">
          <BookOpen className="h-4 w-4 text-cyan" />
        </div>
        <h4 className="font-medium text-sm">
          {concept.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        </h4>
      </div>

      {resources.length > 0 && (
        <div className="space-y-2">
          <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
            Resources
          </span>
          <div className="space-y-1.5">
            {resources.map((res, i) => {
              const Icon = typeIcons[res.type] ?? FileText;
              const color = typeColors[res.type] ?? typeColors.article;
              return (
                <div key={i} className="flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className={cn("text-[10px] shrink-0 capitalize", color)}
                  >
                    <Icon className="h-3 w-3 mr-1" />
                    {res.type}
                  </Badge>
                  {res.url &&
                  (res.url.startsWith("https://") ||
                    res.url.startsWith("http://")) ? (
                    <a
                      href={res.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-cyan hover:underline flex items-center gap-1 truncate"
                    >
                      {res.title}
                      <ExternalLink className="h-3 w-3 shrink-0" />
                    </a>
                  ) : (
                    <span className="text-xs text-muted-foreground truncate">
                      {res.title}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </motion.div>
  );
}
