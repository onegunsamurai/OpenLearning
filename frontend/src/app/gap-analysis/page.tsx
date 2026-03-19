"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageShell } from "@/components/layout/PageShell";
import { RadarChart } from "@/components/gap-analysis/RadarChart";
import { GapCard } from "@/components/gap-analysis/GapCard";
import { GapSummary } from "@/components/gap-analysis/GapSummary";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { useAuthStore } from "@/lib/auth-store";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { ArrowRight, Loader2 } from "lucide-react";

export default function GapAnalysisPage() {
  const router = useRouter();
  const { proficiencyScores, gapAnalysis, setGapAnalysis, setCurrentStep } =
    useAppStore();

  const { user, isLoading: authLoading } = useAuthStore();
  const { login } = useAuth();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      login("/gap-analysis");
      return;
    }
  }, [authLoading, user, login]);

  useEffect(() => {
    if (proficiencyScores.length === 0) {
      router.push("/");
      return;
    }

    if (gapAnalysis) return;

    const fetchGapAnalysis = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.gapAnalysis(proficiencyScores);
        setGapAnalysis(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
      } finally {
        setLoading(false);
      }
    };

    fetchGapAnalysis();
  }, [proficiencyScores, gapAnalysis, setGapAnalysis, router]);

  const handleRetry = async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await api.gapAnalysis(proficiencyScores);
      setGapAnalysis(data);
    } catch {
      setError("Failed again. Please try later.");
    } finally {
      setLoading(false);
    }
  };

  const handleContinue = () => {
    setCurrentStep(3);
    router.push("/learning-plan");
  };

  if (authLoading || !user) return null;
  if (proficiencyScores.length === 0) return null;

  if (loading) {
    return (
      <PageShell currentStep={2}>
        <div className="flex flex-col items-center justify-center py-32 gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-cyan" />
          <p className="text-muted-foreground font-mono text-sm">
            Analyzing skill gaps...
          </p>
          {/* Skeleton */}
          <div className="w-full max-w-4xl grid gap-6 lg:grid-cols-2 mt-8">
            <div className="h-[350px] rounded-xl bg-card border border-border animate-pulse" />
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
      <PageShell currentStep={2}>
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

  if (!gapAnalysis) return null;

  return (
    <PageShell currentStep={2}>
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
        <div className="flex justify-center pb-8">
          <Button
            onClick={handleContinue}
            size="lg"
            className="bg-cyan text-background hover:bg-cyan/90 font-semibold gap-2"
          >
            Generate Learning Plan
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </PageShell>
  );
}
