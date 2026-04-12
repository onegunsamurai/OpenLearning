import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ApiError } from "@/lib/api";
import type { AssessmentReportResponse } from "@/lib/types";

// All mocks used inside vi.mock factories must live in vi.hoisted
const {
  mockRouter,
  mockSetCurrentStep,
  mockReset,
  mockSessionReport,
  mockSearchParams,
  mockStoreState,
} = vi.hoisted(() => {
  return {
    mockRouter: { push: vi.fn(), replace: vi.fn() },
    mockSetCurrentStep: vi.fn(),
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

vi.mock("@/components/gap-analysis/RadarChart", () => ({
  RadarChart: () => <div data-testid="radar-chart">RadarChart</div>,
}));
vi.mock("@/components/gap-analysis/GapCard", () => ({
  GapCard: ({ gap }: { gap: { skillName: string } }) => (
    <div data-testid="gap-card">{gap.skillName}</div>
  ),
}));
vi.mock("@/components/gap-analysis/GapSummary", () => ({
  GapSummary: () => <div data-testid="gap-summary">GapSummary</div>,
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

vi.mock("@/components/gap-analysis/no-gaps-hero", () => ({
  NoGapsHero: ({
    onStartOver,
    onContinue,
    targetLevel,
  }: {
    onStartOver: () => void;
    onContinue: () => void;
    targetLevel: string;
  }) => (
    <div data-testid="no-gaps-hero">
      <span>targetLevel:{targetLevel}</span>
      <button onClick={onStartOver}>Start Over</button>
      <button onClick={onContinue}>View Learning Plan</button>
    </div>
  ),
}));

vi.mock("@/lib/store", () => ({
  useAppStore: () => ({
    assessmentSessionId: mockStoreState.assessmentSessionId,
    setCurrentStep: mockSetCurrentStep,
    targetLevel: mockStoreState.targetLevel,
    reset: mockReset,
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
  proficiencyScores: [
    {
      skillId: "react",
      skillName: "React",
      score: 72,
      confidence: 0.85,
      reasoning: "Good",
    },
  ],
  knowledgeGraph: { nodes: [] },
  gapAnalysis: {
    overallReadiness: 65,
    summary: "Moderate readiness",
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
    summary: "Learn TypeScript",
    totalHours: 20,
    phases: [],
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
    summary: "No significant gaps identified. Great job!",
    gaps: [],
  },
  learningPlan: {
    summary: "No learning needed",
    totalHours: 0,
    phases: [],
  },
};

import GapAnalysisPage from "./page";

beforeEach(() => {
  mockRouter.push.mockClear();
  mockRouter.replace.mockClear();
  mockSetCurrentStep.mockClear();
  mockReset.mockClear();
  mockSessionReport.report = null;
  mockSessionReport.loading = false;
  mockSessionReport.error = null;
  mockSessionReport.refetch.mockClear();
  mockSearchParams.get.mockReturnValue(null);
  mockStoreState.assessmentSessionId = "sess-123";
  mockStoreState.targetLevel = "mid";
});

describe("GapAnalysisPage", () => {
  it("redirects when no session ID", () => {
    mockStoreState.assessmentSessionId = null;
    render(<GapAnalysisPage />);
    expect(mockRouter.push).toHaveBeenCalledWith("/dashboard");
  });

  it("returns null when no session ID", () => {
    mockStoreState.assessmentSessionId = null;
    const { container } = render(<GapAnalysisPage />);
    expect(container.innerHTML).toBe("");
  });

  it("shows loading spinner during fetch", () => {
    mockSessionReport.loading = true;
    render(<GapAnalysisPage />);
    expect(screen.getByText("Loading gap analysis...")).toBeInTheDocument();
  });

  it("renders components on success", () => {
    mockSessionReport.report = sampleReport;
    render(<GapAnalysisPage />);

    expect(screen.getByTestId("radar-chart")).toBeInTheDocument();
    expect(screen.getByTestId("gap-summary")).toBeInTheDocument();
    expect(screen.getByTestId("gap-card")).toBeInTheDocument();
  });

  it("shows error message on failure", () => {
    mockSessionReport.error = new Error("Network error");
    render(<GapAnalysisPage />);
    expect(screen.getByText("Network error")).toBeInTheDocument();
  });

  it("calls refetch on retry", async () => {
    const user = userEvent.setup();
    mockSessionReport.error = new Error("First failure");
    render(<GapAnalysisPage />);

    expect(screen.getByText("First failure")).toBeInTheDocument();

    await user.click(screen.getByText("Retry"));
    expect(mockSessionReport.refetch).toHaveBeenCalled();
  });

  it("continue navigates to learning plan", async () => {
    const user = userEvent.setup();
    mockSessionReport.report = sampleReport;
    render(<GapAnalysisPage />);

    await user.click(screen.getByText("Generate Learning Plan"));

    expect(mockSetCurrentStep).toHaveBeenCalledWith(3);
    expect(mockRouter.push).toHaveBeenCalledWith("/learning-plan?session=sess-123");
  });

  it("uses session search param when provided", () => {
    mockSearchParams.get.mockReturnValue("param-sess");
    mockSessionReport.report = sampleReport;
    render(<GapAnalysisPage />);

    expect(screen.getByTestId("radar-chart")).toBeInTheDocument();
  });

  it("redirects to /assess when report returns 400 (incomplete assessment)", async () => {
    mockSessionReport.error = new ApiError(
      "Assessment not yet complete. Please finish the assessment first.",
      400,
    );
    render(<GapAnalysisPage />);

    await waitFor(() => {
      expect(mockRouter.replace).toHaveBeenCalledWith("/assess?session=sess-123");
    });
  });

  describe("no-gaps success state", () => {
    it("renders NoGapsHero when gaps array is empty", () => {
      mockSessionReport.report = noGapsReport;
      render(<GapAnalysisPage />);
      expect(screen.getByTestId("no-gaps-hero")).toBeInTheDocument();
    });

    it("does not render RadarChart or GapCard when no gaps", () => {
      mockSessionReport.report = noGapsReport;
      render(<GapAnalysisPage />);
      expect(screen.queryByTestId("radar-chart")).not.toBeInTheDocument();
      expect(screen.queryByTestId("gap-card")).not.toBeInTheDocument();
    });

    it("still renders normal layout when gaps exist", () => {
      mockSessionReport.report = sampleReport;
      render(<GapAnalysisPage />);
      expect(screen.queryByTestId("no-gaps-hero")).not.toBeInTheDocument();
      expect(screen.getByTestId("radar-chart")).toBeInTheDocument();
    });

    it("passes targetLevel from store to NoGapsHero", () => {
      mockStoreState.targetLevel = "senior";
      mockSessionReport.report = noGapsReport;
      render(<GapAnalysisPage />);
      expect(screen.getByText("targetLevel:senior")).toBeInTheDocument();
    });

    it("start over calls reset and navigates to /", async () => {
      const user = userEvent.setup();
      mockSessionReport.report = noGapsReport;
      render(<GapAnalysisPage />);

      await user.click(screen.getByText("Start Over"));
      expect(mockReset).toHaveBeenCalled();
      expect(mockRouter.push).toHaveBeenCalledWith("/");
    });

    it("view learning plan navigates correctly", async () => {
      const user = userEvent.setup();
      mockSessionReport.report = noGapsReport;
      render(<GapAnalysisPage />);

      await user.click(screen.getByText("View Learning Plan"));
      expect(mockSetCurrentStep).toHaveBeenCalledWith(3);
      expect(mockRouter.push).toHaveBeenCalledWith("/learning-plan?session=sess-123");
    });
  });
});
