import { client } from "@/lib/generated/api-client/client.gen";
import {
  getSkillsApiSkillsGet,
  parseJdApiParseJdPost,
  gapAnalysisApiGapAnalysisPost,
  learningPlanApiLearningPlanPost,
  getRolesApiRolesGet,
  getRoleApiRolesRoleIdGet,
} from "@/lib/generated/api-client";
import type {
  SkillsResponse,
  JdParseResponse,
  GapAnalysis,
  LearningPlan,
  ProficiencyScore,
  RoleSummary,
  RoleDetail,
} from "@/lib/generated/api-client";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

client.setConfig({ baseUrl: API_URL });

export function unwrap<T>(result: { data?: T; error?: unknown }): T {
  if (result.error !== undefined) {
    const err = result.error as { detail?: string };
    throw new Error(err?.detail ?? "Request failed");
  }
  return result.data as T;
}

export interface AssessmentStartResponse {
  sessionId: string;
  question: string;
  questionType: string;
  step: number;
  totalSteps: number;
}

export interface AssessmentReportResponse {
  knowledgeGraph: {
    nodes: {
      concept: string;
      confidence: number;
      bloomLevel: string;
      prerequisites: string[];
    }[];
  };
  gapNodes: {
    concept: string;
    currentConfidence: number;
    targetBloomLevel: string;
    prerequisites: string[];
  }[];
  learningPlan: {
    summary: string;
    totalHours: number;
    phases: {
      phaseNumber: number;
      title: string;
      concepts: string[];
      rationale: string;
      resources: { type: string; title: string; url: string | null }[];
      estimatedHours: number;
    }[];
  };
  proficiencyScores: ProficiencyScore[];
}

const realApi = {
  getRoles: async (): Promise<RoleSummary[]> =>
    unwrap(await getRolesApiRolesGet()),

  getRole: async (roleId: string): Promise<RoleDetail> =>
    unwrap(await getRoleApiRolesRoleIdGet({ path: { role_id: roleId } })),

  getSkills: async (): Promise<SkillsResponse> =>
    unwrap(await getSkillsApiSkillsGet()),

  parseJD: async (jobDescription: string): Promise<JdParseResponse> =>
    unwrap(
      await parseJdApiParseJdPost({ body: { jobDescription } })
    ),

  gapAnalysis: async (
    proficiencyScores: ProficiencyScore[]
  ): Promise<GapAnalysis> =>
    unwrap(
      await gapAnalysisApiGapAnalysisPost({
        body: { proficiencyScores },
      })
    ),

  learningPlan: async (gapAnalysis: GapAnalysis): Promise<LearningPlan> =>
    unwrap(
      await learningPlanApiLearningPlanPost({
        body: { gapAnalysis },
      })
    ),

  assessmentStart: async (
    skillIds: string[],
    targetLevel?: string,
    roleId?: string | null
  ): Promise<AssessmentStartResponse> => {
    const res = await fetch(`${API_URL}/api/assessment/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skillIds, targetLevel, roleId: roleId ?? undefined }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail ?? `Request failed: ${res.status}`);
    }
    return res.json();
  },

  assessmentRespond: (sessionId: string, response: string) =>
    fetch(`${API_URL}/api/assessment/${sessionId}/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ response }),
    }),

  assessmentReport: async (
    sessionId: string
  ): Promise<AssessmentReportResponse> => {
    const res = await fetch(
      `${API_URL}/api/assessment/${sessionId}/report`
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail ?? `Request failed: ${res.status}`);
    }
    return res.json();
  },

  assessmentExport: async (sessionId: string): Promise<string> => {
    const res = await fetch(`${API_URL}/api/assessment/${sessionId}/export`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail ?? `Request failed: ${res.status}`);
    }
    return res.text();
  },
};

export const api = realApi;
