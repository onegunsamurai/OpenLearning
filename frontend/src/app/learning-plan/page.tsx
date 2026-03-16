"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageShell } from "@/components/layout/PageShell";
import { PlanHeader } from "@/components/learning-plan/PlanHeader";
import { PlanTimeline } from "@/components/learning-plan/PlanTimeline";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Loader2, Copy, RotateCcw, Check, FileDown } from "lucide-react";

export default function LearningPlanPage() {
  const router = useRouter();
  const { gapAnalysis, learningPlan, setLearningPlan, setCurrentStep, reset, assessmentSessionId } =
    useAppStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activePhase, setActivePhase] = useState(1);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!gapAnalysis) {
      router.push("/");
      return;
    }

    if (learningPlan) return;

    const fetchPlan = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.learningPlan(gapAnalysis);
        setLearningPlan(data);
        setCurrentStep(3);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
      } finally {
        setLoading(false);
      }
    };

    fetchPlan();
  }, [gapAnalysis, learningPlan, setLearningPlan, setCurrentStep, router]);

  const handleRetry = async () => {
    if (!gapAnalysis) return;
    setError(null);
    setLoading(true);
    try {
      const data = await api.learningPlan(gapAnalysis);
      setLearningPlan(data);
    } catch {
      setError("Failed again. Please try later.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyPlan = async () => {
    if (!learningPlan) return;
    await navigator.clipboard.writeText(JSON.stringify(learningPlan, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleStartOver = () => {
    reset();
    router.push("/");
  };

  if (!gapAnalysis) return null;

  if (loading) {
    return (
      <PageShell currentStep={3}>
        <div className="flex flex-col items-center justify-center py-32 gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-cyan" />
          <p className="text-muted-foreground font-mono text-sm">
            Generating your learning plan...
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
      <PageShell currentStep={3}>
        <div className="flex flex-col items-center justify-center py-32 gap-4">
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive max-w-md text-center">
            {error}
            <button
              onClick={handleRetry}
              className="ml-2 underline hover:no-underline"
            >
              Retry
            </button>
          </div>
        </div>
      </PageShell>
    );
  }

  if (!learningPlan) return null;

  return (
    <PageShell currentStep={3}>
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
                key={phase.phase}
                onClick={() => setActivePhase(phase.phase)}
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors",
                  activePhase === phase.phase
                    ? "border-cyan bg-cyan-muted text-cyan"
                    : "border-border bg-card text-muted-foreground hover:text-foreground"
                )}
              >
                <span className="font-mono text-xs">Phase {phase.phase}</span>
                <br />
                <span className="font-medium">{phase.name}</span>
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
        {assessmentSessionId && (
          <Button
            asChild
            variant="outline"
            className="gap-2 border-border"
          >
            <a href={`/export/${assessmentSessionId}`} target="_blank" rel="noopener noreferrer">
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
