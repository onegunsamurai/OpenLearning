"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PageShell } from "@/components/layout/PageShell";
import { JDPasteInput } from "@/components/onboarding/JDPasteInput";
import { SkillBrowser } from "@/components/onboarding/SkillBrowser";
import { RoleSelector } from "@/components/onboarding/role-selector";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { Skill } from "@/lib/types";
import { api } from "@/lib/api";
import { ArrowRight, FlaskConical } from "lucide-react";
import { motion } from "motion/react";

export default function OnboardingPage() {
  const router = useRouter();
  const {
    selectedSkillIds,
    toggleSkill,
    setSelectedSkillIds,
    setCurrentStep,
    selectedRoleId,
    setSelectedRoleId,
    roleSkillIds,
    setRoleSkillIds,
    targetLevel,
    setTargetLevel,
    demoMode,
    setDemoMode,
  } = useAppStore();

  const [skills, setSkills] = useState<Skill[]>([]);
  const [categories, setCategories] = useState<string[]>([]);

  // Bootstrap demo mode from URL param and fetch skills.
  // Merged into one effect to prevent a race where the skills fetch
  // hits the real backend before demo mode is activated.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("demo") === "true") {
      setDemoMode(true);
      params.delete("demo");
      const newUrl = params.toString()
        ? `${window.location.pathname}?${params.toString()}`
        : window.location.pathname;
      window.history.replaceState({}, "", newUrl);
      // Return early — setDemoMode will trigger a re-render and this
      // effect will re-run with demoMode=true, fetching from demo API.
      return;
    }

    api.getSkills().then((data) => {
      setSkills(data.skills);
      setCategories(data.categories);
    });
  }, [setDemoMode, demoMode]);

  const handleRoleSelected = useCallback(
    (roleId: string, skillIds: string[]) => {
      setSelectedRoleId(roleId);
      setSelectedSkillIds(skillIds);
      setRoleSkillIds(skillIds);
    },
    [setSelectedRoleId, setSelectedSkillIds, setRoleSkillIds]
  );

  const handleSkillsExtracted = (skillIds: string[]) => {
    const merged = [...new Set([...selectedSkillIds, ...skillIds])];
    setSelectedSkillIds(merged);
    setSelectedRoleId(null);
    setRoleSkillIds([]);
  };

  const handleStart = () => {
    setCurrentStep(1);
    router.push("/assess");
  };

  const selectedNames = selectedSkillIds
    .map((id) => skills.find((s) => s.id === id)?.name)
    .filter(Boolean);

  const isModified =
    selectedRoleId !== null &&
    (selectedSkillIds.length !== roleSkillIds.length ||
      !selectedSkillIds.every((id) => roleSkillIds.includes(id)));

  return (
    <PageShell currentStep={0}>
      <div className="grid gap-10 lg:grid-cols-2 lg:gap-16">
        {/* Left: Hero */}
        <motion.div
          className="flex flex-col justify-center"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h2 className="font-heading text-4xl font-bold tracking-tight sm:text-5xl">
            Discover your{" "}
            <span className="text-gradient">skill gaps</span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
            Select a role, paste a job description, or choose skills manually.
            Our AI will assess your proficiency, identify gaps, and generate a
            personalized learning plan.
          </p>
          <div className="mt-6 space-y-2">
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-muted text-xs font-mono text-cyan">
                1
              </span>
              Select a role or choose skills
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
              onTargetLevelChange={setTargetLevel}
            />
          </div>

          <div className="flex items-center gap-4">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs font-mono text-muted-foreground uppercase">
              or paste a JD
            </span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <div className="rounded-xl border border-border bg-card p-6">
            <h3 className="mb-4 font-heading text-lg font-semibold">
              Paste a Job Description
            </h3>
            <JDPasteInput
              skills={skills}
              selectedSkillIds={selectedSkillIds}
              onSkillsExtracted={handleSkillsExtracted}
              onToggleSkill={toggleSkill}
            />
          </div>

          <div className="flex items-center gap-4">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs font-mono text-muted-foreground uppercase">
              or browse manually
            </span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <div className="rounded-xl border border-border bg-card p-6">
            <h3 className="mb-4 font-heading text-lg font-semibold">
              Select Skills
            </h3>
            <SkillBrowser
              skills={skills}
              categories={categories}
              selectedSkillIds={selectedSkillIds}
              onToggleSkill={toggleSkill}
            />
          </div>
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
            <button
              type="button"
              aria-pressed={demoMode}
              onClick={() => setDemoMode(!demoMode)}
              className={`flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-mono transition-colors ${
                demoMode
                  ? "border-amber-500/50 bg-amber-500/10 text-amber-400"
                  : "border-border text-muted-foreground hover:text-foreground"
              }`}
              title={demoMode ? "Disable demo mode" : "Enable demo mode (no API key needed)"}
            >
              <FlaskConical className="h-3 w-3" />
              Demo
            </button>
            {selectedSkillIds.length === 0 ? (
              "Select at least 1 skill to continue"
            ) : (
              <>
                <span className="font-semibold text-cyan">
                  {selectedSkillIds.length}
                </span>{" "}
                skill{selectedSkillIds.length !== 1 && "s"} selected
                {isModified && (
                  <span className="ml-1 text-yellow-500">(modified)</span>
                )}
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
            disabled={selectedSkillIds.length === 0}
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
