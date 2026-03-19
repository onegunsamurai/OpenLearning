import { client } from "@/lib/generated/api-client/client.gen";
import {
  getSkillsApiSkillsGet,
  gapAnalysisApiGapAnalysisPost,
  learningPlanApiLearningPlanPost,
  getRolesApiRolesGet,
  getRoleApiRolesRoleIdGet,
  authMeApiAuthMeGet,
  authLogoutApiAuthLogoutPost,
  setApiKeyApiAuthApiKeyPost,
  getApiKeyApiAuthApiKeyGet,
} from "@/lib/generated/api-client";
import type {
  SkillsResponse,
  GapAnalysis,
  LearningPlan,
  ProficiencyScore,
  RoleSummary,
  RoleDetail,
  AuthMeResponse,
  ApiKeyResponse,
} from "@/lib/generated/api-client";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

client.setConfig({ baseUrl: API_URL, credentials: "include" });

export function unwrap<T>(result: { data?: T; error?: unknown }): T {
  if (result.error !== undefined) {
    const err = result.error as { detail?: string };
    throw new Error(err?.detail ?? "Request failed");
  }
  return result.data as T;
}

/** Wrapper around fetch that always sends credentials (cookies). */
function authFetch(url: string, init?: RequestInit): Promise<Response> {
  return fetch(url, { ...init, credentials: "include" });
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
    const res = await authFetch(`${API_URL}/api/assessment/start`, {
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
    authFetch(`${API_URL}/api/assessment/${sessionId}/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ response }),
    }),

  assessmentReport: async (
    sessionId: string
  ): Promise<AssessmentReportResponse> => {
    const res = await authFetch(
      `${API_URL}/api/assessment/${sessionId}/report`
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail ?? `Request failed: ${res.status}`);
    }
    return res.json();
  },

  assessmentExport: async (sessionId: string): Promise<string> => {
    const res = await authFetch(`${API_URL}/api/assessment/${sessionId}/export`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail ?? `Request failed: ${res.status}`);
    }
    return res.text();
  },

  // Auth methods
  authMe: async (): Promise<AuthMeResponse> =>
    unwrap(await authMeApiAuthMeGet()),

  authLogout: async (): Promise<void> => {
    await authLogoutApiAuthLogoutPost();
  },

  authSetApiKey: async (apiKey: string): Promise<void> => {
    unwrap(await setApiKeyApiAuthApiKeyPost({ body: { apiKey } }));
  },

  authGetApiKey: async (): Promise<ApiKeyResponse> =>
    unwrap(await getApiKeyApiAuthApiKeyGet()),
};

export const api = realApi;
