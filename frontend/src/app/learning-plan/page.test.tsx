import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import type { AssessmentReportResponse } from "@/lib/types";

const {
  mockRouter,
  mockReset,
  mockSessionReport,
  mockSearchParams,
  mockStoreState,
} = vi.hoisted(() => {
  return {
    mockRouter: { push: vi.fn() },
    mockReset: vi.fn(),
    mockSessionReport: {
      report: null as AssessmentReportResponse | null,
      loading: false,
      error: null as Error | null,
      refetch: vi.fn(),
    },
    mockSearchParams: { get: vi.fn().mockReturnValue(null) },
    mockStoreState: {
      assessmentSessionId: "sess-123" as string | null,
      targetLevel: "mid",
    },
  };
});

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => mockSearchParams,
}));

vi.mock("@/components/learning-plan/PlanHeader", () => ({
  PlanHeader: () => <div data-testid="plan-header">PlanHeader</div>,
}));
vi.mock("@/components/learning-plan/PlanTimeline", () => ({
  PlanTimeline: () => <div data-testid="plan-timeline">PlanTimeline</div>,
}));
vi.mock("@/components/layout/PageShell", () => ({
  PageShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useApiKeySetupContext: () => ({ openApiKeySetup: vi.fn() }),
}));
vi.mock("@/components/error/api-error-display", () => ({
  ApiErrorDisplay: ({ error, onRetry }: { error: Error; onRetry?: () => void }) => (
    <div data-testid="api-error-display">
      <span>{error.message}</span>
      {onRetry && <button onClick={onRetry}>Retry</button>}
    </div>
  ),
}));

vi.mock("@/components/learning-plan/no-gaps-success", () => ({
  NoGapsSuccess: ({
    onStartOver,
    targetLevel,
    scores,
  }: {
    onStartOver: () => void;
    targetLevel: string;
    scores: { skillId: string }[];
  }) => (
    <div data-testid="no-gaps-success">
      <span>targetLevel:{targetLevel}</span>
      <span>{scores.length} scores</span>
      <button onClick={onStartOver}>Start Over</button>
    </div>
  ),
}));

vi.mock("@/lib/store", () => ({
  useAppStore: () => ({
    assessmentSessionId: mockStoreState.assessmentSessionId,
    reset: mockReset,
    targetLevel: mockStoreState.targetLevel,
  }),
}));

vi.mock("@/hooks/useSessionReport", () => ({
  useSessionReport: () => mockSessionReport,
}));

vi.mock("@/lib/auth-store", () => ({
  useAuthStore: () => ({ user: { userId: "u1", displayName: "test", avatarUrl: "", hasApiKey: false, email: null }, isLoading: false }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ login: vi.fn(), logout: vi.fn() }),
}));

const sampleReport: AssessmentReportResponse = {
  proficiencyScores: [],
  knowledgeGraph: { nodes: [] },
  gapAnalysis: {
    overallReadiness: 50,
    summary: "Needs work",
    gaps: [
      {
        skillId: "typescript",
        skillName: "TypeScript",
        currentLevel: 40,
        targetLevel: 80,
        gap: 40,
        priority: "high",
        recommendation: "Study generics",
      },
    ],
  },
  learningPlan: {
    summary: "Master TypeScript in 4 weeks",
    totalHours: 48,
    phases: [
      {
        phaseNumber: 1,
        title: "Foundations",
        concepts: [
          {
            key: "core-types",
            name: "Core types",
            description: "",
            resources: [],
          },
        ],
        rationale: "Core skills",
        estimatedHours: 8,
      },
      {
        phaseNumber: 2,
        title: "Advanced",
        concepts: [
          {
            key: "generics",
            name: "Generics",
            description: "",
            resources: [],
          },
        ],
        rationale: "Advanced patterns",
        estimatedHours: 10,
      },
    ],
  },
};

const noGapsReport: AssessmentReportResponse = {
  proficiencyScores: [
    {
      skillId: "react",
      skillName: "React",
      score: 95,
      confidence: 0.9,
      reasoning: "Excellent",
    },
  ],
  knowledgeGraph: { nodes: [] },
  gapAnalysis: {
    overallReadiness: 100,
    summary: "No gaps",
    gaps: [],
  },
  learningPlan: {
    summary: "No learning needed",
    totalHours: 0,
    phases: [],
  },
};

import LearningPlanPage from "./page";

beforeEach(() => {
  mockRouter.push.mockClear();
  mockReset.mockClear();
  mockSessionReport.report = null;
  mockSessionReport.loading = false;
  mockSessionReport.error = null;
  mockSessionReport.refetch.mockClear();
  mockSearchParams.get.mockReturnValue(null);
  mockStoreState.assessmentSessionId = "sess-123";
  mockStoreState.targetLevel = "mid";
});

describe("LearningPlanPage", () => {
  it("redirects when no session ID", () => {
    mockStoreState.assessmentSessionId = null;
    render(<LearningPlanPage />);
    expect(mockRouter.push).toHaveBeenCalledWith("/dashboard");
  });

  it("shows loading during fetch", () => {
    mockSessionReport.loading = true;
    render(<LearningPlanPage />);
    expect(
      screen.getByText("Loading your learning plan...")
    ).toBeInTheDocument();
  });

  it("shows error with retry", () => {
    mockSessionReport.error = new Error("API error");
    render(<LearningPlanPage />);
    expect(screen.getByText("API error")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("calls refetch on retry", async () => {
    const user = userEvent.setup();
    mockSessionReport.error = new Error("First fail");
    render(<LearningPlanPage />);

    expect(screen.getByText("First fail")).toBeInTheDocument();

    await user.click(screen.getByText("Retry"));
    expect(mockSessionReport.refetch).toHaveBeenCalled();
  });

  it("renders plan components on success", () => {
    mockSessionReport.report = sampleReport;
    render(<LearningPlanPage />);

    expect(screen.getByTestId("plan-header")).toBeInTheDocument();
    expect(screen.getByTestId("plan-timeline")).toBeInTheDocument();
  });

  it("phase navigation buttons render", () => {
    mockSessionReport.report = sampleReport;
    render(<LearningPlanPage />);

    expect(screen.getByText("Foundations")).toBeInTheDocument();
    expect(screen.getByText("Advanced")).toBeInTheDocument();
  });

  it("clicking phase button works", async () => {
    const user = userEvent.setup();
    mockSessionReport.report = sampleReport;
    render(<LearningPlanPage />);

    // Click phase 2
    const phase2Btn = screen.getByText("Advanced").closest("button")!;
    await user.click(phase2Btn);

    // Phase 2 button should have the active class
    expect(phase2Btn.className).toContain("border-cyan");
  });

  it("copy plan writes clipboard", async () => {
    const user = userEvent.setup();
    mockSessionReport.report = sampleReport;

    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", {
      ...navigator,
      clipboard: { writeText: writeTextMock },
    });

    render(<LearningPlanPage />);

    await user.click(screen.getByText("Save Plan (JSON)"));

    expect(writeTextMock).toHaveBeenCalledWith(
      JSON.stringify(sampleReport.learningPlan, null, 2)
    );

    vi.unstubAllGlobals();
  });

  it("copy shows confirmation then resets", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockSessionReport.report = sampleReport;

    vi.stubGlobal("navigator", {
      ...navigator,
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });

    render(<LearningPlanPage />);

    await user.click(screen.getByText("Save Plan (JSON)"));

    await waitFor(() => {
      expect(screen.getByText("Copied!")).toBeInTheDocument();
    });

    vi.advanceTimersByTime(2000);

    await waitFor(() => {
      expect(screen.getByText("Save Plan (JSON)")).toBeInTheDocument();
    });

    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("export button shown when session id exists", () => {
    mockSessionReport.report = sampleReport;
    render(<LearningPlanPage />);

    expect(screen.getByText("Export Report")).toBeInTheDocument();
  });

  it("shows export button when session comes from search param", () => {
    mockStoreState.assessmentSessionId = null;
    // With no sessionId at all, the page redirects — so this scenario
    // can only happen if session comes from search params.
    // Since the page renders Export Report whenever sessionId is truthy,
    // and sessionId = sessionParam || assessmentSessionId, if both are null
    // the page redirects. So test that the link exists when session present.
    mockSearchParams.get.mockReturnValue("param-sess");
    mockSessionReport.report = sampleReport;
    render(<LearningPlanPage />);
    expect(screen.getByText("Export Report")).toBeInTheDocument();
  });

  it("start over resets and navigates", async () => {
    const user = userEvent.setup();
    mockSessionReport.report = sampleReport;
    render(<LearningPlanPage />);

    await user.click(screen.getByText("Start Over"));

    expect(mockReset).toHaveBeenCalled();
    expect(mockRouter.push).toHaveBeenCalledWith("/");
  });

  describe("no-gaps success state", () => {
    it("renders NoGapsSuccess when gaps array is empty", () => {
      mockSessionReport.report = noGapsReport;
      render(<LearningPlanPage />);
      expect(screen.getByTestId("no-gaps-success")).toBeInTheDocument();
    });

    it("does not render PlanHeader or PlanTimeline when no phases", () => {
      mockSessionReport.report = noGapsReport;
      render(<LearningPlanPage />);
      expect(screen.queryByTestId("plan-header")).not.toBeInTheDocument();
      expect(screen.queryByTestId("plan-timeline")).not.toBeInTheDocument();
    });

    it("still renders normal layout when phases exist", () => {
      mockSessionReport.report = sampleReport;
      render(<LearningPlanPage />);
      expect(screen.queryByTestId("no-gaps-success")).not.toBeInTheDocument();
      expect(screen.getByTestId("plan-header")).toBeInTheDocument();
    });

    it("passes targetLevel from store", () => {
      mockStoreState.targetLevel = "staff";
      mockSessionReport.report = noGapsReport;
      render(<LearningPlanPage />);
      expect(screen.getByText("targetLevel:staff")).toBeInTheDocument();
    });

    it("passes proficiency scores", () => {
      mockSessionReport.report = noGapsReport;
      render(<LearningPlanPage />);
      expect(screen.getByText("1 scores")).toBeInTheDocument();
    });

    it("start over in success state calls reset and navigates", async () => {
      const user = userEvent.setup();
      mockSessionReport.report = noGapsReport;
      render(<LearningPlanPage />);

      await user.click(screen.getByText("Start Over"));
      expect(mockReset).toHaveBeenCalled();
      expect(mockRouter.push).toHaveBeenCalledWith("/");
    });
  });
});
