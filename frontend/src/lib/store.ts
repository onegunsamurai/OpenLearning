import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { ProficiencyScore, GapAnalysis, LearningPlan } from "./types";

interface AppState {
  // Step tracking
  currentStep: number;
  setCurrentStep: (step: number) => void;

  // Onboarding
  selectedSkillIds: string[];
  toggleSkill: (skillId: string) => void;
  setSelectedSkillIds: (ids: string[]) => void;
  selectedRoleId: string | null;
  setSelectedRoleId: (roleId: string | null) => void;
  roleSkillIds: string[];
  setRoleSkillIds: (ids: string[]) => void;
  targetLevel: string;
  setTargetLevel: (level: string) => void;

  // Assessment
  assessmentSessionId: string | null;
  setAssessmentSessionId: (id: string) => void;
  proficiencyScores: ProficiencyScore[];
  setProficiencyScores: (scores: ProficiencyScore[]) => void;

  // Gap Analysis
  gapAnalysis: GapAnalysis | null;
  setGapAnalysis: (analysis: GapAnalysis) => void;

  // Learning Plan
  learningPlan: LearningPlan | null;
  setLearningPlan: (plan: LearningPlan) => void;

  // Reset
  reset: () => void;
}

export const initialState = {
  currentStep: 0,
  selectedSkillIds: [],
  selectedRoleId: null as string | null,
  roleSkillIds: [] as string[],
  targetLevel: "mid",
  assessmentSessionId: null as string | null,
  proficiencyScores: [],
  gapAnalysis: null,
  learningPlan: null,
};

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      ...initialState,

      setCurrentStep: (step) => set({ currentStep: step }),

      toggleSkill: (skillId) =>
        set((state) => ({
          selectedSkillIds: state.selectedSkillIds.includes(skillId)
            ? state.selectedSkillIds.filter((id) => id !== skillId)
            : [...state.selectedSkillIds, skillId],
        })),

      setSelectedSkillIds: (ids) => set({ selectedSkillIds: ids }),
      setSelectedRoleId: (roleId) => set({ selectedRoleId: roleId }),
      setRoleSkillIds: (ids) => set({ roleSkillIds: ids }),
      setTargetLevel: (level) => set({ targetLevel: level }),

      setAssessmentSessionId: (id) => set({ assessmentSessionId: id }),
      setProficiencyScores: (scores) => set({ proficiencyScores: scores }),

      setGapAnalysis: (analysis) => set({ gapAnalysis: analysis }),
      setLearningPlan: (plan) => set({ learningPlan: plan }),

      reset: () => set(initialState),
    }),
    {
      name: "open-learning-store",
      storage: createJSONStorage(() => sessionStorage),
    }
  )
);
