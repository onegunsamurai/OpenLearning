import type { AssessmentReportResponse } from "../../src/lib/api";

export const MOCK_SESSION_ID = "e2e-mock-session-001";

export const MOCK_AUTH_ME = {
  userId: "test-user-id",
  displayName: "E2E Test",
  avatarUrl: "",
  hasApiKey: true,
  email: "e2e-test@openlearning.test",
};

export const MOCK_START_RESPONSE = {
  sessionId: MOCK_SESSION_ID,
  question:
    "Let's start with a calibration question. Can you describe your experience with REST API design?",
  questionType: "calibration",
  step: 1,
  totalSteps: 3,
};

export const MOCK_REPORT: AssessmentReportResponse = {
  knowledgeGraph: {
    nodes: [
      {
        concept: "REST API Design",
        confidence: 0.75,
        bloomLevel: "apply",
        prerequisites: [],
      },
      {
        concept: "Database Optimization",
        confidence: 0.45,
        bloomLevel: "understand",
        prerequisites: ["REST API Design"],
      },
      {
        concept: "System Architecture",
        confidence: 0.6,
        bloomLevel: "analyze",
        prerequisites: ["REST API Design", "Database Optimization"],
      },
    ],
  },
  gapAnalysis: {
    overallReadiness: 62,
    summary:
      "You have solid foundations in API design but need to strengthen database optimization and system-level thinking.",
    gaps: [
      {
        skillId: "db-optimization",
        skillName: "Database Optimization",
        currentLevel: 45,
        targetLevel: 80,
        gap: 35,
        priority: "critical",
        recommendation:
          "Focus on query optimization, indexing strategies, and connection pooling.",
      },
      {
        skillId: "system-arch",
        skillName: "System Architecture",
        currentLevel: 60,
        targetLevel: 85,
        gap: 25,
        priority: "high",
        recommendation:
          "Study distributed system patterns and scalability principles.",
      },
      {
        skillId: "rest-api",
        skillName: "REST API Design",
        currentLevel: 75,
        targetLevel: 85,
        gap: 10,
        priority: "medium",
        recommendation:
          "Deepen knowledge of advanced REST patterns like HATEOAS and content negotiation.",
      },
    ],
  },
  learningPlan: {
    summary:
      "A structured 2-phase plan to close your skill gaps over approximately 40 hours.",
    totalHours: 40,
    phases: [
      {
        phaseNumber: 1,
        title: "Foundations",
        concepts: ["Query Optimization", "Indexing", "Connection Pooling"],
        rationale:
          "Database optimization is your biggest gap and a prerequisite for system architecture.",
        resources: [
          {
            type: "course",
            title: "Database Performance Fundamentals",
            url: null,
          },
          {
            type: "article",
            title: "PostgreSQL Indexing Best Practices",
            url: null,
          },
        ],
        estimatedHours: 25,
      },
      {
        phaseNumber: 2,
        title: "Advanced Patterns",
        concepts: [
          "Distributed Systems",
          "Scalability",
          "Advanced REST Patterns",
        ],
        rationale:
          "With database skills in place, tackle system architecture and advanced API design.",
        resources: [
          {
            type: "book",
            title: "Designing Data-Intensive Applications",
            url: null,
          },
          {
            type: "course",
            title: "System Design Fundamentals",
            url: null,
          },
        ],
        estimatedHours: 15,
      },
    ],
  },
  proficiencyScores: [
    {
      skillId: "rest-api",
      skillName: "REST API Design",
      score: 75,
      confidence: 0.85,
      reasoning: "Strong understanding of core REST principles and HTTP methods.",
    },
    {
      skillId: "db-optimization",
      skillName: "Database Optimization",
      score: 45,
      confidence: 0.78,
      reasoning:
        "Basic SQL knowledge but gaps in indexing and query optimization.",
    },
    {
      skillId: "system-arch",
      skillName: "System Architecture",
      score: 60,
      confidence: 0.72,
      reasoning:
        "Understands monolithic design; needs exposure to distributed patterns.",
    },
  ],
};

/** Zustand store state for sessionStorage seeding. */
export const MOCK_STORE_STATE = {
  state: {
    currentStep: 1,
    selectedSkillIds: ["rest-api", "db-optimization", "system-arch"],
    selectedRoleId: "backend_engineering",
    roleSkillIds: ["rest-api", "db-optimization", "system-arch"],
    targetLevel: "mid",
    assessmentSessionId: null as string | null,
  },
  version: 0,
};

// ---------------------------------------------------------------------------
// SSE helpers
// ---------------------------------------------------------------------------

/** Build an SSE response body with a text message and optional META JSON. */
export function buildSSEResponse(
  text: string,
  meta?: Record<string, unknown>
): string {
  let body = `data: ${text}\n\n`;
  if (meta) {
    body += `data: [META]${JSON.stringify(meta)}\n\n`;
  }
  body += "data: [DONE]\n\n";
  return body;
}

/** SSE response that marks assessment as complete. */
export function buildSSEComplete(): string {
  return `data: Great work! You've completed all the assessment questions.\n\ndata: [ASSESSMENT_COMPLETE]\n\ndata: [DONE]\n\n`;
}

/** SSE response that signals an error. */
export function buildSSEError(detail: string, status = 500): string {
  return `data: [ERROR]${JSON.stringify({ detail, status })}\n\ndata: [DONE]\n\n`;
}
