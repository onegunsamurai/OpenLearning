import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import type { GapAnalysis, LearningPlan } from "@/lib/types";

const {
  mockState,
  mockRouter,
  mockSetLearningPlan,
  mockSetCurrentStep,
  mockReset,
  mockLearningPlanApi,
} = vi.hoisted(() => {
  const mockSetLearningPlan = vi.fn();
  const state = {
    gapAnalysis: null as GapAnalysis | null,
    learningPlan: null as LearningPlan | null,
    assessmentSessionId: null as string | null,
  };
  mockSetLearningPlan.mockImplementation((data: LearningPlan) => {
    state.learningPlan = data;
  });
  return {
    mockState: state,
    mockRouter: { push: vi.fn() },
    mockSetLearningPlan,
    mockSetCurrentStep: vi.fn(),
    mockReset: vi.fn(),
    mockLearningPlanApi: vi.fn(),
  };
});

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
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

vi.mock("@/lib/store", () => ({
  useAppStore: () => ({
    gapAnalysis: mockState.gapAnalysis,
    learningPlan: mockState.learningPlan,
    setLearningPlan: mockSetLearningPlan,
    setCurrentStep: mockSetCurrentStep,
    reset: mockReset,
    assessmentSessionId: mockState.assessmentSessionId,
  }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/api")>();
  return {
    ApiError: mod.ApiError,
    api: {
      learningPlan: (...args: unknown[]) => mockLearningPlanApi(...args),
    },
  };
});

vi.mock("@/lib/auth-store", () => ({
  useAuthStore: () => ({ user: { userId: "u1", displayName: "test", avatarUrl: "", hasApiKey: false, email: null }, isLoading: false }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ login: vi.fn(), logout: vi.fn() }),
}));

const sampleGapAnalysis: GapAnalysis = {
  overallReadiness: 50,
  summary: "Needs work",
  gaps: [
    {
      skillId: "ts",
      skillName: "TypeScript",
      currentLevel: 30,
      targetLevel: 80,
      gap: 50,
      priority: "high",
      recommendation: "Study generics",
    },
  ],
};

const samplePlan: LearningPlan = {
  title: "TypeScript Mastery",
  summary: "Master TypeScript in 4 weeks",
  totalHours: 30,
  totalWeeks: 4,
  phases: [
    {
      phase: 1,
      name: "Foundations",
      description: "Core skills",
      modules: [
        {
          id: "m1",
          title: "Basics",
          description: "Core types",
          type: "theory",
          phase: 1,
          skillIds: ["ts"],
          durationHours: 8,
          objectives: ["Understand types"],
          resources: ["https://typescriptlang.org"],
        },
      ],
    },
    {
      phase: 2,
      name: "Advanced",
      description: "Advanced patterns",
      modules: [
        {
          id: "m2",
          title: "Generics",
          description: "Generic types",
          type: "lab",
          phase: 2,
          skillIds: ["ts"],
          durationHours: 10,
          objectives: ["Use generics"],
          resources: [],
        },
      ],
    },
  ],
};

import LearningPlanPage from "./page";

beforeEach(() => {
  mockRouter.push.mockClear();
  mockSetLearningPlan.mockClear();
  mockSetLearningPlan.mockImplementation((data: LearningPlan) => {
    mockState.learningPlan = data;
  });
  mockSetCurrentStep.mockClear();
  mockReset.mockClear();
  mockLearningPlanApi.mockReset();
  mockState.gapAnalysis = sampleGapAnalysis;
  mockState.learningPlan = null;
  mockState.assessmentSessionId = null;
});

describe("LearningPlanPage", () => {
  it("redirects when no gap analysis", () => {
    mockState.gapAnalysis = null;
    render(<LearningPlanPage />);
    expect(mockRouter.push).toHaveBeenCalledWith("/");
  });

  it("shows loading during fetch", () => {
    mockLearningPlanApi.mockImplementation(() => new Promise(() => {}));
    render(<LearningPlanPage />);
    expect(
      screen.getByText("Generating your learning plan...")
    ).toBeInTheDocument();
  });

  it("shows error with retry", async () => {
    mockLearningPlanApi.mockRejectedValueOnce(new Error("API error"));
    render(<LearningPlanPage />);
    await waitFor(() => {
      expect(screen.getByText("API error")).toBeInTheDocument();
      expect(screen.getByText("Retry")).toBeInTheDocument();
    });
  });

  it("calls api on retry", async () => {
    const user = userEvent.setup();
    mockLearningPlanApi.mockRejectedValueOnce(new Error("First fail"));
    render(<LearningPlanPage />);

    await waitFor(() => {
      expect(screen.getByText("First fail")).toBeInTheDocument();
    });

    mockLearningPlanApi.mockResolvedValueOnce(samplePlan);
    await user.click(screen.getByText("Retry"));

    await waitFor(() => {
      expect(mockSetLearningPlan).toHaveBeenCalledWith(samplePlan);
    });
  });

  it("shows retry failure message", async () => {
    const user = userEvent.setup();
    mockLearningPlanApi.mockRejectedValueOnce(new Error("First"));
    render(<LearningPlanPage />);

    await waitFor(() => {
      expect(screen.getByText("First")).toBeInTheDocument();
    });

    mockLearningPlanApi.mockRejectedValueOnce(new Error("Second failure"));
    await user.click(screen.getByText("Retry"));

    await waitFor(() => {
      expect(screen.getByText("Second failure")).toBeInTheDocument();
    });
  });

  it("renders plan components on success", async () => {
    mockLearningPlanApi.mockResolvedValueOnce(samplePlan);
    render(<LearningPlanPage />);

    await waitFor(() => {
      expect(screen.getByTestId("plan-header")).toBeInTheDocument();
      expect(screen.getByTestId("plan-timeline")).toBeInTheDocument();
    });
  });

  it("skips fetch when cached", () => {
    mockState.learningPlan = samplePlan;
    render(<LearningPlanPage />);
    expect(mockLearningPlanApi).not.toHaveBeenCalled();
    expect(screen.getByTestId("plan-header")).toBeInTheDocument();
  });

  it("phase navigation buttons render", async () => {
    mockState.learningPlan = samplePlan;
    render(<LearningPlanPage />);

    expect(screen.getByText("Foundations")).toBeInTheDocument();
    expect(screen.getByText("Advanced")).toBeInTheDocument();
  });

  it("clicking phase button works", async () => {
    const user = userEvent.setup();
    mockState.learningPlan = samplePlan;
    render(<LearningPlanPage />);

    // Click phase 2
    const phase2Btn = screen.getByText("Advanced").closest("button")!;
    await user.click(phase2Btn);

    // Phase 2 button should have the active class
    expect(phase2Btn.className).toContain("border-cyan");
  });

  it("copy plan writes clipboard", async () => {
    const user = userEvent.setup();
    mockState.learningPlan = samplePlan;

    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", {
      ...navigator,
      clipboard: { writeText: writeTextMock },
    });

    render(<LearningPlanPage />);

    await user.click(screen.getByText("Save Plan (JSON)"));

    expect(writeTextMock).toHaveBeenCalledWith(
      JSON.stringify(samplePlan, null, 2)
    );

    vi.unstubAllGlobals();
  });

  it("copy shows confirmation then resets", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockState.learningPlan = samplePlan;

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
    mockState.learningPlan = samplePlan;
    mockState.assessmentSessionId = "sess-123";
    render(<LearningPlanPage />);

    expect(screen.getByText("Export Report")).toBeInTheDocument();
  });

  it("export button hidden when no session id", () => {
    mockState.learningPlan = samplePlan;
    mockState.assessmentSessionId = null;
    render(<LearningPlanPage />);

    expect(screen.queryByText("Export Report")).not.toBeInTheDocument();
  });

  it("start over resets and navigates", async () => {
    const user = userEvent.setup();
    mockState.learningPlan = samplePlan;
    render(<LearningPlanPage />);

    await user.click(screen.getByText("Start Over"));

    expect(mockReset).toHaveBeenCalled();
    expect(mockRouter.push).toHaveBeenCalledWith("/");
  });
});
