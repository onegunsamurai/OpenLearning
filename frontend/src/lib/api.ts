import { client } from "@/lib/generated/api-client/client.gen";
import {
  getSkillsApiSkillsGet,
  parseJdApiParseJdPost,
  gapAnalysisApiGapAnalysisPost,
  learningPlanApiLearningPlanPost,
} from "@/lib/generated/api-client";
import type {
  SkillsResponse,
  JdParseResponse,
  GapAnalysis,
  LearningPlan,
  ProficiencyScore,
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

export const api = {
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

  assessStream: (
    messages: { role: string; content: string }[],
    skillNames: string[]
  ) =>
    fetch(`${API_URL}/api/assess`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages, skillNames }),
    }),

  assessmentStart: async (
    skillIds: string[],
    targetLevel?: string
  ): Promise<AssessmentStartResponse> => {
    const res = await fetch(`${API_URL}/api/assessment/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skillIds, targetLevel }),
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
};
