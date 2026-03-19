"use client";

import { StepProgress, type StepDefinition } from "./StepProgress";
import { motion } from "motion/react";
import Image from "next/image";
import Link from "next/link";
import { Play, LogOut, Github } from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { useAuth } from "@/hooks/useAuth";

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
  const { user, isLoading } = useAuthStore();
  const { login, logout } = useAuth();

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

          <div className="flex items-center gap-4">
            {!isDemo && (
              <div className="flex items-center gap-2">
                {isLoading ? (
                  <div className="h-8 w-24 animate-pulse rounded-full bg-muted" />
                ) : user ? (
                  <div className="flex items-center gap-2">
                    {user.avatarUrl && (
                      <Image
                        src={user.avatarUrl}
                        alt={user.githubUsername}
                        width={28}
                        height={28}
                        className="h-7 w-7 rounded-full border border-border"
                      />
                    )}
                    <span className="hidden text-sm text-muted-foreground sm:block">
                      {user.githubUsername}
                    </span>
                    <button
                      onClick={logout}
                      className="inline-flex h-8 items-center gap-1.5 rounded-full border border-border px-3 text-xs text-muted-foreground transition-colors hover:text-foreground"
                    >
                      <LogOut className="h-3 w-3" />
                      <span className="hidden sm:inline">Sign Out</span>
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => login(window.location.pathname)}
                    className="inline-flex h-8 items-center gap-1.5 rounded-full border border-border px-3.5 text-[13px] font-medium text-muted-foreground transition-colors hover:text-foreground"
                  >
                    <Github className="h-3.5 w-3.5" />
                    Sign in with GitHub
                  </button>
                )}
              </div>
            )}
            <StepProgress currentStep={currentStep} steps={steps} />
          </div>
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
