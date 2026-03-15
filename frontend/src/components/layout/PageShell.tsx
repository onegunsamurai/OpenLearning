"use client";

import { StepProgress } from "./StepProgress";
import { useAppStore } from "@/lib/store";
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
  const demoMode = useAppStore((s) => s.demoMode);

  return (
    <div className="grid-background min-h-screen">
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
        <div className={`mx-auto flex items-center justify-between ${maxWidth} px-4 py-3 sm:px-6`}>
          <div className="flex items-center gap-3">
            <h1 className="font-heading text-lg font-bold tracking-tight">
              <span className="text-cyan">Open</span>Learning
            </h1>
            {demoMode ? (
              <span className="rounded border border-amber-500/50 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-amber-400">
                Demo
              </span>
            ) : (
              <span className="hidden text-xs text-muted-foreground font-mono sm:block">
                session resets on close
              </span>
            )}
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
