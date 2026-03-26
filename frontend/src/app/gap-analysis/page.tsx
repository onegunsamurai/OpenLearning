"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PageShell } from "@/components/layout/PageShell";
import { RadarChart } from "@/components/gap-analysis/RadarChart";
import { GapCard } from "@/components/gap-analysis/GapCard";
import { GapSummary } from "@/components/gap-analysis/GapSummary";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { useAuthStore } from "@/lib/auth-store";
import { useAuth } from "@/hooks/useAuth";
import { useSessionReport } from "@/hooks/useSessionReport";
import { ApiErrorDisplay } from "@/components/error/api-error-display";
import { ArrowRight, Loader2, Eye } from "lucide-react";

export default function GapAnalysisPage() {
  return (
    <Suspense>
      <GapAnalysisPageContent />
    </Suspense>
  );
}

function GapAnalysisPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionParam = searchParams.get("session");

  const { assessmentSessionId, setCurrentStep } = useAppStore();
  const { user, isLoading: authLoading } = useAuthStore();
  const { login } = useAuth();

  const sessionId = sessionParam || assessmentSessionId;
  const { report, loading, error, refetch } = useSessionReport(sessionId);

  useEffect(() => {
    if (!authLoading && !user) {
      login("/gap-analysis" + (sessionParam ? `?session=${sessionParam}` : ""));
      return;
    }
  }, [authLoading, user, login, sessionParam]);

  useEffect(() => {
    if (!sessionId && !authLoading && user) {
      router.push("/dashboard");
    }
  }, [sessionId, authLoading, user, router]);

  const handleContinue = () => {
    setCurrentStep(3);
    router.push(`/learning-plan${sessionId ? `?session=${sessionId}` : ""}`);
  };

  if (authLoading || !user) return null;
  if (!sessionId) return null;

  if (loading) {
    return (
      <PageShell currentStep={2} sessionId={sessionId}>
        <div className="flex flex-col items-center justify-center py-32 gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-cyan" />
          <p className="text-muted-foreground font-mono text-sm">
            Loading gap analysis...
          </p>
          <div className="w-full max-w-4xl grid gap-6 lg:grid-cols-2 mt-8">
            <div className="h-[250px] sm:h-[350px] rounded-xl bg-card border border-border animate-pulse" />
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="h-24 rounded-xl bg-card border border-border animate-pulse"
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
      <PageShell currentStep={2} sessionId={sessionId}>
        <div className="flex flex-col items-center justify-center py-32 gap-4">
          <ApiErrorDisplay error={error} onRetry={refetch} />
        </div>
      </PageShell>
    );
  }

  if (!report) return null;

  const { gapAnalysis } = report;

  return (
    <PageShell currentStep={2} sessionId={sessionId}>
      <div className="space-y-8">
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Left: Chart + Readiness */}
          <div className="space-y-6">
            <div className="rounded-xl border border-border bg-card p-6">
              <RadarChart gaps={gapAnalysis.gaps} />
            </div>
            <GapSummary
              readiness={gapAnalysis.overallReadiness}
              summary={gapAnalysis.summary}
            />
          </div>

          {/* Right: Gap Cards */}
          <div className="space-y-4">
            <h3 className="font-heading text-xl font-semibold">
              Skill Gap Breakdown
            </h3>
            {gapAnalysis.gaps.map((gap, i) => (
              <GapCard key={gap.skillId} gap={gap} index={i} />
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="flex flex-col items-center gap-3 pb-8 sm:flex-row sm:justify-center">
          <Button
            onClick={handleContinue}
            size="lg"
            className="bg-cyan text-background hover:bg-cyan/90 font-semibold gap-2"
          >
            Generate Learning Plan
            <ArrowRight className="h-4 w-4" />
          </Button>
          {report.learningPlan && report.learningPlan.phases.length > 0 && (
            <Button
              onClick={handleContinue}
              size="lg"
              variant="outline"
              className="gap-2 border-border"
            >
              <Eye className="h-4 w-4" />
              View Learning Plan
            </Button>
          )}
        </div>
      </div>
    </PageShell>
  );
}
