"use client";

import { StepProgress, type StepDefinition } from "./StepProgress";
import { motion } from "motion/react";
import Link from "next/link";
import { Play } from "lucide-react";

interface PageShellProps {
  currentStep: number;
  children: React.ReactNode;
  maxWidth?: string;
  noPadding?: boolean;
  isDemo?: boolean;
  steps?: StepDefinition[];
}

export function PageShell({
  currentStep,
  children,
  maxWidth = "max-w-7xl",
  noPadding = false,
  isDemo = false,
  steps,
}: PageShellProps) {
  return (
    <div className="grid-background min-h-screen">
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
        <div className={`mx-auto flex items-center justify-between ${maxWidth} px-4 py-3 sm:px-6`}>
          <div className="flex items-center gap-3">
            <h1 className="font-heading text-lg font-bold tracking-tight">
              <span className="text-cyan">Open</span>Learning
            </h1>
            {isDemo ? (
              <span className="rounded border border-amber-500/50 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-amber-400">
                Demo
              </span>
            ) : (
              <>
                <span className="hidden text-xs text-muted-foreground font-mono sm:block">
                  session resets on close
                </span>
                <Link
                  href="/demo/assess"
                  className="inline-flex h-8 items-center gap-1.5 rounded-full bg-cyan-400 px-3.5 text-[13px] font-semibold text-[#0a0a1a] shadow-[0_0_12px_rgba(34,211,238,0.35)] transition-all duration-200 hover:shadow-[0_0_20px_rgba(34,211,238,0.5)] hover:brightness-110"
                >
                  <Play className="h-3 w-3 fill-current" />
                  Try Demo
                </Link>
              </>
            )}
          </div>
          <StepProgress currentStep={currentStep} steps={steps} />
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
