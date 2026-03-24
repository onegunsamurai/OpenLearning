import { client } from "@/lib/generated/api-client/client.gen";
import {
  getSkillsApiSkillsGet,
  getRolesApiRolesGet,
  getRoleApiRolesRoleIdGet,
  authMeApiAuthMeGet,
  authLogoutApiAuthLogoutPost,
  setApiKeyApiAuthApiKeyPost,
  getApiKeyApiAuthApiKeyGet,
  deleteApiKeyApiAuthApiKeyDelete,
  validateKeyApiAuthValidateKeyPost,
  registerApiAuthRegisterPost,
  loginApiAuthLoginPost,
  listUserAssessmentsApiUserAssessmentsGet,
} from "@/lib/generated/api-client";
import type {
  SkillsResponse,
  RoleSummary,
  RoleDetail,
  AuthMeResponse,
  ApiKeyResponse,
  ValidateKeyResponse,
  UserAssessmentSummary,
} from "@/lib/generated/api-client";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

client.setConfig({ baseUrl: API_URL, credentials: "include" });

export function parseRetryAfter(
  value: string | null | undefined
): number | undefined {
  if (!value) return undefined;
  const n = Number(value);
  if (!Number.isNaN(n) && n >= 0) return Math.ceil(n);
  // HTTP-date format (RFC 7231)
  const ms = Date.parse(value);
  if (!Number.isNaN(ms)) {
    const delta = Math.ceil((ms - Date.now()) / 1000);
    return delta > 0 ? delta : undefined;
  }
  return undefined;
}

export class ApiError extends Error {
  status: number;
  retryAfter?: number;

  constructor(message: string, status: number, retryAfter?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

async function throwFromResponse(
  res: Response,
  fallback: string
): Promise<never> {
  const err = await res.json().catch(() => ({ detail: fallback }));
  const retryAfter = res.headers?.get("Retry-After");
  throw new ApiError(
    err.detail ?? fallback,
    res.status,
    parseRetryAfter(retryAfter)
  );
}

export function unwrap<T>(result: {
  data?: T;
  error?: unknown;
  response?: Response;
}): T {
  if (result.error !== undefined) {
    const err = result.error as { detail?: string };
    const status = result.response?.status ?? 500;
    const retryAfter = result.response?.headers?.get("Retry-After");
    throw new ApiError(
      err?.detail ?? "Request failed",
      status,
      parseRetryAfter(retryAfter)
    );
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
  gapAnalysis: {
    overallReadiness: number;
    summary: string;
    gaps: {
      skillId: string;
      skillName: string;
      currentLevel: number;
      targetLevel: number;
      gap: number;
      priority: "critical" | "high" | "medium" | "low";
      recommendation: string;
    }[];
  };
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
  proficiencyScores: {
    skillId: string;
    skillName: string;
    score: number;
    confidence: number;
    reasoning: string;
  }[];
}

const realApi = {
  getRoles: async (): Promise<RoleSummary[]> =>
    unwrap(await getRolesApiRolesGet()),

  getRole: async (roleId: string): Promise<RoleDetail> =>
    unwrap(await getRoleApiRolesRoleIdGet({ path: { role_id: roleId } })),

  getSkills: async (): Promise<SkillsResponse> =>
    unwrap(await getSkillsApiSkillsGet()),

  getUserAssessments: async (): Promise<UserAssessmentSummary[]> =>
    unwrap(await listUserAssessmentsApiUserAssessmentsGet()),

  assessmentResume: async (
    sessionId: string
  ): Promise<AssessmentStartResponse> => {
    const res = await authFetch(
      `${API_URL}/api/assessment/${sessionId}/resume`
    );
    if (!res.ok) await throwFromResponse(res, "Failed to resume assessment");
    return res.json();
  },

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
    if (!res.ok) await throwFromResponse(res, "Request failed");
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
    if (!res.ok) await throwFromResponse(res, "Request failed");
    return res.json();
  },

  assessmentExport: async (sessionId: string): Promise<string> => {
    const res = await authFetch(`${API_URL}/api/assessment/${sessionId}/export`);
    if (!res.ok) await throwFromResponse(res, "Request failed");
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

  authDeleteApiKey: async (): Promise<void> => {
    unwrap(await deleteApiKeyApiAuthApiKeyDelete());
  },

  authValidateKey: async (apiKey: string): Promise<ValidateKeyResponse> =>
    unwrap(await validateKeyApiAuthValidateKeyPost({ body: { apiKey } })),

  authRegister: async (email: string, password: string): Promise<void> => {
    unwrap(await registerApiAuthRegisterPost({ body: { email, password } }));
  },

  authLogin: async (email: string, password: string): Promise<void> => {
    unwrap(await loginApiAuthLoginPost({ body: { email, password } }));
  },
};

export const api = realApi;
