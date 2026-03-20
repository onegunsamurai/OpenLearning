"use client";

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
}

export function StepProgress({ currentStep, steps = defaultSteps }: StepProgressProps) {
  return (
    <div className="flex items-center gap-1 sm:gap-2">
      {steps.map((step, index) => (
        <div key={step.label} className="flex items-center gap-1 sm:gap-2">
          <div className="flex items-center gap-1 sm:gap-2">
            <motion.div
              className={cn(
                "flex h-6 w-6 sm:h-8 sm:w-8 items-center justify-center rounded-full text-[10px] sm:text-xs font-mono font-semibold transition-colors",
                index < currentStep
                  ? "bg-cyan text-background"
                  : index === currentStep
                    ? "border-2 border-cyan text-cyan"
                    : "border border-border text-muted-foreground"
              )}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: index * 0.1 }}
            >
              {index < currentStep ? "✓" : index + 1}
            </motion.div>
            <span
              className={cn(
                "hidden text-sm font-medium sm:block",
                index <= currentStep
                  ? "text-foreground"
                  : "text-muted-foreground"
              )}
            >
              {step.label}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div className="relative h-[2px] w-4 sm:w-8 md:w-12 bg-border">
              {index < currentStep && (
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
      ))}
    </div>
  );
}
