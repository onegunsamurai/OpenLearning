"use client";

import { useEffect, useCallback, useReducer } from "react";
import { useRouter } from "next/navigation";
import { PageShell } from "@/components/layout/PageShell";
import { ConceptBrowser } from "@/components/onboarding/ConceptBrowser";
import { RoleSelector } from "@/components/onboarding/role-selector";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { api } from "@/lib/api";
import { ArrowRight, Play, Loader2 } from "lucide-react";
import Link from "next/link";
import { motion } from "motion/react";
import type { ConceptSummary } from "@/lib/types";

const MAX_CONCEPTS = 10;

export default function OnboardingPage() {
  const router = useRouter();
  const {
    selectedSkillIds,
    toggleSkill,
    setSelectedSkillIds,
    setCurrentStep,
    selectedRoleId,
    setSelectedRoleId,
    setRoleSkillIds,
    targetLevel,
    setTargetLevel,
  } = useAppStore();

  type ConceptsAction =
    | { type: "loading" }
    | { type: "loaded"; concepts: ConceptSummary[] }
    | { type: "error" };

  const [conceptsState, dispatchConcepts] = useReducer(
    (_: { concepts: ConceptSummary[]; loading: boolean }, action: ConceptsAction) => {
      switch (action.type) {
        case "loading": return { concepts: [], loading: true };
        case "loaded": return { concepts: action.concepts, loading: false };
        case "error": return { concepts: [], loading: false };
      }
    },
    { concepts: [], loading: false }
  );

  // Fetch concepts when role or target level changes
  useEffect(() => {
    if (!selectedRoleId) return;
    let cancelled = false;
    dispatchConcepts({ type: "loading" });
    api
      .getRoleConcepts(selectedRoleId, targetLevel)
      .then((data) => {
        if (!cancelled) dispatchConcepts({ type: "loaded", concepts: data.concepts });
      })
      .catch(() => {
        if (!cancelled) dispatchConcepts({ type: "error" });
      });
    return () => { cancelled = true; };
  }, [selectedRoleId, targetLevel]);

  const { concepts, loading: loadingConcepts } = conceptsState;

  const handleRoleSelected = useCallback(
    (roleId: string, _skillIds: string[]) => {
      setSelectedRoleId(roleId);
      // Clear previous concept selections when role changes
      setSelectedSkillIds([]);
      setRoleSkillIds([]);
    },
    [setSelectedRoleId, setSelectedSkillIds, setRoleSkillIds]
  );

  const handleTargetLevelChange = useCallback(
    (level: string) => {
      setTargetLevel(level);
      // Clear selections when level changes (different concepts available)
      setSelectedSkillIds([]);
    },
    [setTargetLevel, setSelectedSkillIds]
  );

  const handleToggleConcept = useCallback(
    (conceptId: string) => {
      if (
        selectedSkillIds.length >= MAX_CONCEPTS &&
        !selectedSkillIds.includes(conceptId)
      ) {
        return;
      }
      toggleSkill(conceptId);
    },
    [selectedSkillIds, toggleSkill]
  );

  const handleStart = () => {
    setCurrentStep(1);
    router.push("/assess");
  };

  // Build display names for the bottom bar
  const selectedNames = selectedSkillIds
    .map((id) => concepts.find((c) => c.id === id)?.displayName)
    .filter(Boolean);

  return (
    <PageShell autoPromptApiKey>
      <div className="grid gap-10 pb-24 lg:grid-cols-2 lg:gap-16">
        {/* Left: Hero */}
        <motion.div
          className="flex flex-col justify-center"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h2 className="font-heading text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Discover your{" "}
            <span className="text-gradient">skill gaps</span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
            Select a role, then choose the topics you want to be assessed on.
            Our AI will evaluate your proficiency and generate a personalized
            learning plan.
          </p>
          <div className="mt-6 space-y-2">
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-muted text-xs font-mono text-cyan">
                1
              </span>
              Select a role and pick topics
            </div>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-muted text-xs font-mono text-cyan">
                2
              </span>
              Chat-based skill assessment
            </div>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-muted text-xs font-mono text-cyan">
                3
              </span>
              Get your gap analysis & learning plan
            </div>
          </div>
          <div className="mt-8 flex flex-col items-start gap-2">
            <Link
              href="/demo/assess"
              className="inline-flex min-h-[48px] items-center gap-2.5 rounded-full bg-gradient-to-br from-cyan-400 to-emerald-300 px-8 text-base font-semibold text-[#0a0a1a] transition-all duration-200 hover:scale-[1.03] hover:brightness-110"
            >
              <Play className="h-4 w-4 fill-current" />
              Try Interactive Demo
            </Link>
            <span className="pl-2 text-[13px] text-muted-foreground">
              No signup required &middot; 2 min walkthrough
            </span>
          </div>
        </motion.div>

        {/* Right: Input Panel */}
        <motion.div
          className="space-y-6"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <div className="rounded-xl border border-border bg-card p-6 glow-cyan">
            <h3 className="mb-4 font-heading text-lg font-semibold">
              Select a Role
            </h3>
            <RoleSelector
              selectedRoleId={selectedRoleId}
              onSelectRole={handleRoleSelected}
              targetLevel={targetLevel}
              onTargetLevelChange={handleTargetLevelChange}
            />
          </div>

          {selectedRoleId && (
            <motion.div
              className="rounded-xl border border-border bg-card p-6"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <h3 className="mb-4 font-heading text-lg font-semibold">
                Select Topics to Assess
              </h3>
              {loadingConcepts ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  <span className="ml-2 text-sm text-muted-foreground">
                    Loading topics...
                  </span>
                </div>
              ) : (
                <ConceptBrowser
                  concepts={concepts}
                  selectedConceptIds={selectedSkillIds}
                  onToggleConcept={handleToggleConcept}
                  maxSelections={MAX_CONCEPTS}
                />
              )}
            </motion.div>
          )}
        </motion.div>
      </div>

      {/* Bottom bar */}
      <motion.div
        className="fixed bottom-0 left-0 right-0 border-t border-border bg-background/90 backdrop-blur-md"
        initial={{ y: 100 }}
        animate={{ y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            {selectedSkillIds.length === 0 ? (
              selectedRoleId
                ? "Select at least 1 topic to continue"
                : "Select a role to see available topics"
            ) : (
              <>
                <span className="font-semibold text-cyan">
                  {selectedSkillIds.length}
                </span>{" "}
                topic{selectedSkillIds.length !== 1 && "s"} selected
                {selectedNames.length > 0 && (
                  <span className="hidden sm:inline">
                    {" "}
                    — {selectedNames.slice(0, 3).join(", ")}
                    {selectedNames.length > 3 &&
                      ` +${selectedNames.length - 3} more`}
                  </span>
                )}
              </>
            )}
          </div>
          <Button
            onClick={handleStart}
            disabled={selectedSkillIds.length === 0 || !selectedRoleId}
            className="bg-cyan text-background hover:bg-cyan/90 font-semibold gap-2"
          >
            Start Assessment
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </motion.div>
    </PageShell>
  );
}
