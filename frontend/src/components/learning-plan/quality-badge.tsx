"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { QUALITY_THRESHOLDS, QUALITY_LABELS } from "@/lib/constants";

interface QualityBadgeProps {
  qualityScore: number;
  qualityFlag: string | null;
}

function getQualityLevel(score: number, flag: string | null) {
  if (flag) return QUALITY_LABELS.flagged;
  if (score >= QUALITY_THRESHOLDS.high) return QUALITY_LABELS.high;
  if (score >= QUALITY_THRESHOLDS.acceptable) return QUALITY_LABELS.acceptable;
  return QUALITY_LABELS.low;
}

export function QualityBadge({ qualityScore, qualityFlag }: QualityBadgeProps) {
  const level = getQualityLevel(qualityScore, qualityFlag);

  return (
    <Badge variant="outline" className={cn("text-[10px]", level.color)}>
      {level.text}
    </Badge>
  );
}
