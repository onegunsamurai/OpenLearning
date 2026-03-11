"use client";

import { StepProgress } from "./StepProgress";
import { motion } from "motion/react";

interface PageShellProps {
  currentStep: number;
  children: React.ReactNode;
  maxWidth?: string;
  noPadding?: boolean;
}

export function PageShell({
  currentStep,
  children,
  maxWidth = "max-w-7xl",
  noPadding = false,
}: PageShellProps) {
  return (
    <div className="grid-background min-h-screen">
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
        <div className={`mx-auto flex items-center justify-between ${maxWidth} px-4 py-3 sm:px-6`}>
          <div className="flex items-center gap-3">
            <h1 className="font-heading text-lg font-bold tracking-tight">
              <span className="text-cyan">Open</span>Learning
            </h1>
            <span className="hidden text-xs text-muted-foreground font-mono sm:block">
              session resets on close
            </span>
          </div>
          <StepProgress currentStep={currentStep} />
        </div>
      </header>
      <motion.main
        className={noPadding ? "" : `mx-auto ${maxWidth} px-4 py-8 sm:px-6`}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
      >
        {children}
      </motion.main>
    </div>
  );
}
