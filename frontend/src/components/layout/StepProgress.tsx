"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { motion } from "motion/react";

export interface StepDefinition {
  label: string;
  path: string;
}

const defaultSteps: StepDefinition[] = [
  { label: "Skills", path: "/" },
  { label: "Assess", path: "/assess" },
  { label: "Gaps", path: "/gap-analysis" },
  { label: "Plan", path: "/learning-plan" },
];

interface StepProgressProps {
  currentStep: number;
  steps?: StepDefinition[];
  sessionId?: string | null;
}

export function StepProgress({ currentStep, steps = defaultSteps, sessionId }: StepProgressProps) {
  function buildHref(path: string): string {
    if (!sessionId || path === "/") return path;
    return `${path}?session=${sessionId}`;
  }

  return (
    <div className="flex items-center gap-1 sm:gap-2">
      {steps.map((step, index) => {
        const isCompleted = index < currentStep;
        const isCurrent = index === currentStep;
        const isClickable = isCompleted && !isCurrent;

        const indicator = (
          <>
            <motion.div
              className={cn(
                "flex h-6 w-6 sm:h-8 sm:w-8 items-center justify-center rounded-full text-[10px] sm:text-xs font-mono font-semibold transition-colors",
                isCompleted
                  ? "bg-cyan text-background"
                  : isCurrent
                    ? "border-2 border-cyan text-cyan"
                    : "border border-border text-muted-foreground",
                isClickable && "hover:bg-cyan/80 cursor-pointer"
              )}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: index * 0.1 }}
            >
              {isCompleted ? "✓" : index + 1}
            </motion.div>
            <span
              className={cn(
                "hidden text-sm font-medium sm:block",
                index <= currentStep
                  ? "text-foreground"
                  : "text-muted-foreground",
                isClickable && "hover:text-cyan cursor-pointer"
              )}
            >
              {step.label}
            </span>
          </>
        );

        return (
          <div key={step.label} className="flex items-center gap-1 sm:gap-2">
            {isClickable ? (
              <Link href={buildHref(step.path)} className="flex items-center gap-1 sm:gap-2">
                {indicator}
              </Link>
            ) : (
              <div className="flex items-center gap-1 sm:gap-2">
                {indicator}
              </div>
            )}
            {index < steps.length - 1 && (
              <div className="relative h-[2px] w-4 sm:w-8 md:w-12 bg-border">
                {isCompleted && (
                  <motion.div
                    className="absolute inset-0 bg-cyan"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 0.4, delay: index * 0.15 }}
                    style={{ transformOrigin: "left" }}
                  />
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
