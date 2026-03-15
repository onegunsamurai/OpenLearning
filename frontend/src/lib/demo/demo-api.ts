import type {
  SkillsResponse,
  RoleSummary,
  RoleDetail,
  JdParseResponse,
  GapAnalysis,
  LearningPlan,
  ProficiencyScore,
} from "@/lib/types";
import type { AssessmentStartResponse, AssessmentReportResponse } from "@/lib/api";
import {
  DEMO_SKILLS,
  DEMO_ROLES,
  DEMO_ROLE_DETAIL,
  DEMO_JD_PARSE,
  DEMO_GAP_ANALYSIS,
  DEMO_LEARNING_PLAN,
  DEMO_ASSESSMENT_START,
  DEMO_ASSESSMENT_REPORT,
  DEMO_QUESTIONS,
} from "./fixtures";
import { createDemoSSEResponse } from "./demo-assessment";
import { useAppStore } from "@/lib/store";

/** Simulate a short network delay (100-200ms). */
function fakeDelay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 100 + Math.random() * 100));
}

export const demoApi = {
  getRoles: async (): Promise<RoleSummary[]> => {
    await fakeDelay();
    return DEMO_ROLES;
  },

  getRole: async (_roleId: string): Promise<RoleDetail> => {
    await fakeDelay();
    return DEMO_ROLE_DETAIL;
  },

  getSkills: async (): Promise<SkillsResponse> => {
    await fakeDelay();
    return DEMO_SKILLS;
  },

  parseJD: async (_jobDescription: string): Promise<JdParseResponse> => {
    await fakeDelay();
    return DEMO_JD_PARSE;
  },

  gapAnalysis: async (
    _proficiencyScores: ProficiencyScore[]
  ): Promise<GapAnalysis> => {
    await fakeDelay();
    return DEMO_GAP_ANALYSIS;
  },

  learningPlan: async (_gapAnalysis: GapAnalysis): Promise<LearningPlan> => {
    await fakeDelay();
    return DEMO_LEARNING_PLAN;
  },

  assessmentStart: async (
    _skillIds: string[],
    _targetLevel?: string,
    _roleId?: string | null
  ): Promise<AssessmentStartResponse> => {
    // Reset demo step counter on new session
    useAppStore.getState().resetDemoStep();
    await fakeDelay();
    return DEMO_ASSESSMENT_START;
  },

  assessmentRespond: (_sessionId: string, _response: string): Promise<Response> => {
    const step = useAppStore.getState().demoStep;
    const isFinal = step >= DEMO_QUESTIONS.length - 1;
    useAppStore.getState().advanceDemoStep();
    return Promise.resolve(createDemoSSEResponse(step, isFinal));
  },

  assessmentReport: async (
    _sessionId: string
  ): Promise<AssessmentReportResponse> => {
    await fakeDelay();
    return DEMO_ASSESSMENT_REPORT;
  },
};
