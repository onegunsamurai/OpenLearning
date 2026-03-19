"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PageShell } from "@/components/layout/PageShell";
import { SkillBrowser } from "@/components/onboarding/SkillBrowser";
import { RoleSelector } from "@/components/onboarding/role-selector";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { Skill } from "@/lib/types";
import { api } from "@/lib/api";
import { ArrowRight, Play } from "lucide-react";
import Link from "next/link";
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
  } = useAppStore();

  const [skills, setSkills] = useState<Skill[]>([]);
  const [categories, setCategories] = useState<string[]>([]);

  useEffect(() => {
    api.getSkills().then((data) => {
      setSkills(data.skills);
      setCategories(data.categories);
    });
  }, []);

  const handleRoleSelected = useCallback(
    (roleId: string, skillIds: string[]) => {
      setSelectedRoleId(roleId);
      setSelectedSkillIds(skillIds);
      setRoleSkillIds(skillIds);
    },
    [setSelectedRoleId, setSelectedSkillIds, setRoleSkillIds]
  );

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
    <PageShell autoPromptApiKey>
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
            Select a role or choose skills manually. Our AI will assess your
            proficiency, identify gaps, and generate a personalized learning
            plan.
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
              onTargetLevelChange={setTargetLevel}
            />
          </div>

          <div className="flex items-center gap-4">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs font-mono text-muted-foreground uppercase">
              or browse skills
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
