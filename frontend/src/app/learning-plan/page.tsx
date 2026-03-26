"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PageShell } from "@/components/layout/PageShell";
import { PlanHeader } from "@/components/learning-plan/PlanHeader";
import { PlanTimeline } from "@/components/learning-plan/PlanTimeline";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { useAuthStore } from "@/lib/auth-store";
import { useAuth } from "@/hooks/useAuth";
import { useSessionReport } from "@/hooks/useSessionReport";
import { ApiErrorDisplay } from "@/components/error/api-error-display";
import { cn } from "@/lib/utils";
import { Loader2, Copy, RotateCcw, Check, FileDown, ArrowLeft } from "lucide-react";

export default function LearningPlanPage() {
  return (
    <Suspense>
      <LearningPlanPageContent />
    </Suspense>
  );
}

function LearningPlanPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionParam = searchParams.get("session");

  const { assessmentSessionId, reset } = useAppStore();
  const { user, isLoading: authLoading } = useAuthStore();
  const { login } = useAuth();

  const sessionId = sessionParam || assessmentSessionId;
  const { report, loading, error, refetch } = useSessionReport(sessionId);

  const [activePhase, setActivePhase] = useState(1);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      login(
        "/learning-plan" + (sessionParam ? `?session=${sessionParam}` : "")
      );
      return;
    }
  }, [authLoading, user, login, sessionParam]);

  useEffect(() => {
    if (!sessionId && !authLoading && user) {
      router.push("/dashboard");
    }
  }, [sessionId, authLoading, user, router]);

  const handleCopyPlan = async () => {
    if (!report?.learningPlan) return;
    await navigator.clipboard.writeText(
      JSON.stringify(report.learningPlan, null, 2)
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleBackToGaps = () => {
    router.push(`/gap-analysis${sessionId ? `?session=${sessionId}` : ""}`);
  };

  const handleStartOver = () => {
    reset();
    router.push("/");
  };

  if (authLoading || !user) return null;
  if (!sessionId) return null;

  if (loading) {
    return (
      <PageShell currentStep={3} sessionId={sessionId}>
        <div className="flex flex-col items-center justify-center py-32 gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-cyan" />
          <p className="text-muted-foreground font-mono text-sm">
            Loading your learning plan...
          </p>
          <div className="w-full max-w-4xl grid gap-4 lg:grid-cols-[250px,1fr] mt-8">
            <div className="h-[300px] rounded-xl bg-card border border-border animate-pulse" />
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className="h-28 rounded-xl bg-card border border-border animate-pulse"
                />
              ))}
            </div>
          </div>
        </div>
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell currentStep={3} sessionId={sessionId}>
        <div className="flex flex-col items-center justify-center py-32 gap-4">
          <ApiErrorDisplay error={error} onRetry={refetch} />
        </div>
      </PageShell>
    );
  }

  if (!report) return null;

  const { learningPlan } = report;

  return (
    <PageShell currentStep={3} sessionId={sessionId}>
      <div className="grid gap-8 lg:grid-cols-[260px,1fr]">
        {/* Left sidebar */}
        <aside className="space-y-6">
          <PlanHeader plan={learningPlan} />

          {/* Phase navigation */}
          <div className="space-y-2">
            <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
              Phases
            </h4>
            {learningPlan.phases.map((phase) => (
              <button
                key={phase.phaseNumber}
                onClick={() => setActivePhase(phase.phaseNumber)}
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors",
                  activePhase === phase.phaseNumber
                    ? "border-cyan bg-cyan-muted text-cyan"
                    : "border-border bg-card text-muted-foreground hover:text-foreground"
                )}
              >
                <span className="font-mono text-xs">
                  Phase {phase.phaseNumber}
                </span>
                <br />
                <span className="font-medium">{phase.title}</span>
              </button>
            ))}
          </div>
        </aside>

        {/* Main content */}
        <div className="space-y-6">
          <PlanTimeline plan={learningPlan} activePhase={activePhase} />
        </div>
      </div>

      {/* Footer */}
      <div className="mt-12 flex flex-col items-center gap-4 border-t border-border pt-8 pb-8 sm:flex-row sm:justify-center">
        <Button
          onClick={handleBackToGaps}
          variant="outline"
          className="gap-2 border-border"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Gap Analysis
        </Button>
        <Button
          onClick={handleCopyPlan}
          variant="outline"
          className="gap-2 border-border"
        >
          {copied ? (
            <Check className="h-4 w-4 text-green-400" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
          {copied ? "Copied!" : "Save Plan (JSON)"}
        </Button>
        {sessionId && (
          <Button
            asChild
            variant="outline"
            className="gap-2 border-border"
          >
            <a
              href={`/export/${sessionId}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <FileDown className="h-4 w-4" />
              Export Report
            </a>
          </Button>
        )}
        <Button
          onClick={handleStartOver}
          variant="outline"
          className="gap-2 border-border text-muted-foreground"
        >
          <RotateCcw className="h-4 w-4" />
          Start Over
        </Button>
      </div>
    </PageShell>
  );
}
