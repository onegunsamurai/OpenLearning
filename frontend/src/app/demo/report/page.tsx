"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PageShell } from "@/components/layout/PageShell";
import { RadarChart } from "@/components/gap-analysis/RadarChart";
import { GapCard } from "@/components/gap-analysis/GapCard";
import { GapSummary } from "@/components/gap-analysis/GapSummary";
import { PlanHeader } from "@/components/learning-plan/PlanHeader";
import { PlanTimeline } from "@/components/learning-plan/PlanTimeline";
import { Button } from "@/components/ui/button";
import {
  DEMO_GAP_ANALYSIS,
  DEMO_LEARNING_PLAN,
  DEMO_EXPORT_MARKDOWN,
  DEMO_PROFICIENCY_SCORES,
} from "@/lib/demo/fixtures";
import { cn } from "@/lib/utils";
import { DEMO_STEPS } from "@/lib/demo/constants";
import { ArrowRight, Download, RotateCcw } from "lucide-react";
import { motion } from "motion/react";

export default function DemoReportPage() {
  const router = useRouter();
  const [activePhase, setActivePhase] = useState(1);
  const [section, setSection] = useState<"gaps" | "plan">("gaps");

  const gapAnalysis = DEMO_GAP_ANALYSIS;
  const learningPlan = DEMO_LEARNING_PLAN;

  const handleDownload = () => {
    const blob = new Blob([DEMO_EXPORT_MARKDOWN], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "demo-assessment-report.md";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <PageShell currentStep={1} isDemo steps={DEMO_STEPS}>
      {/* Section tabs */}
      <div className="flex gap-2 mb-8">
        <button
          type="button"
          onClick={() => setSection("gaps")}
          className={cn(
            "rounded-lg border px-4 py-2 text-sm font-semibold transition-colors",
            section === "gaps"
              ? "border-cyan bg-cyan-muted text-cyan"
              : "border-border bg-card text-muted-foreground hover:text-foreground"
          )}
        >
          Gap Analysis
        </button>
        <button
          type="button"
          onClick={() => setSection("plan")}
          className={cn(
            "rounded-lg border px-4 py-2 text-sm font-semibold transition-colors",
            section === "plan"
              ? "border-cyan bg-cyan-muted text-cyan"
              : "border-border bg-card text-muted-foreground hover:text-foreground"
          )}
        >
          Learning Plan
        </button>
      </div>

      {section === "gaps" && (
        <motion.div
          className="space-y-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {/* Proficiency summary */}
          <div className="rounded-xl border border-border bg-card p-4">
            <h3 className="font-heading text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">
              Proficiency Scores
            </h3>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-5">
              {DEMO_PROFICIENCY_SCORES.map((s) => (
                <div key={s.skillId} className="text-center">
                  <div className="text-lg font-mono font-bold text-cyan">{s.score}%</div>
                  <div className="text-xs text-muted-foreground">{s.skillName}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-8 lg:grid-cols-2">
            <div className="space-y-6">
              <div className="rounded-xl border border-border bg-card p-6">
                <RadarChart gaps={gapAnalysis.gaps} />
              </div>
              <GapSummary
                readiness={gapAnalysis.overallReadiness}
                summary={gapAnalysis.summary}
              />
            </div>
            <div className="space-y-4">
              <h3 className="font-heading text-xl font-semibold">
                Skill Gap Breakdown
              </h3>
              {gapAnalysis.gaps.map((gap, i) => (
                <GapCard key={gap.skillId} gap={gap} index={i} />
              ))}
            </div>
          </div>

          <div className="flex justify-center">
            <Button
              onClick={() => setSection("plan")}
              className="bg-cyan text-background hover:bg-cyan/90 font-semibold gap-2"
            >
              View Learning Plan
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </motion.div>
      )}

      {section === "plan" && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <div className="grid gap-8 lg:grid-cols-[260px,1fr]">
            <aside className="space-y-6">
              <PlanHeader plan={learningPlan} />
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
            <div className="space-y-6">
              <PlanTimeline plan={learningPlan} activePhase={activePhase} />
            </div>
          </div>
        </motion.div>
      )}

      {/* Footer */}
      <div className="mt-12 flex flex-col items-center gap-4 border-t border-border pt-8 pb-8 sm:flex-row sm:justify-center">
        <Button
          onClick={handleDownload}
          variant="outline"
          className="gap-2 border-border"
        >
          <Download className="h-4 w-4" />
          Download Report (.md)
        </Button>
        <Button
          onClick={() => {
            sessionStorage.removeItem("demo-onboarding-seen");
            router.push("/demo/assess");
          }}
          variant="outline"
          className="gap-2 border-border text-muted-foreground"
        >
          <RotateCcw className="h-4 w-4" />
          Start Over
        </Button>
        <Button
          onClick={() => router.push("/")}
          className="bg-cyan text-background hover:bg-cyan/90 font-semibold gap-2"
        >
          Try the Real Thing
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </PageShell>
  );
}
