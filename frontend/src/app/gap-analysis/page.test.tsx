import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import type { GapAnalysis, ProficiencyScore } from "@/lib/types";

// All mocks used inside vi.mock factories must live in vi.hoisted
const {
  mockState,
  mockRouter,
  mockSetGapAnalysis,
  mockSetCurrentStep,
  mockGapAnalysisApi,
} = vi.hoisted(() => {
  const mockSetGapAnalysis = vi.fn();
  const state = {
    scores: [] as ProficiencyScore[],
    gapAnalysis: null as GapAnalysis | null,
  };
  mockSetGapAnalysis.mockImplementation((data: GapAnalysis) => {
    state.gapAnalysis = data;
  });
  return {
    mockState: state,
    // STABLE router reference — prevents useEffect re-firing on every render
    mockRouter: { push: vi.fn() },
    mockSetGapAnalysis,
    mockSetCurrentStep: vi.fn(),
    mockGapAnalysisApi: vi.fn(),
  };
});

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
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
}));

vi.mock("@/lib/store", () => ({
  useAppStore: () => ({
    proficiencyScores: mockState.scores,
    gapAnalysis: mockState.gapAnalysis,
    setGapAnalysis: mockSetGapAnalysis,
    setCurrentStep: mockSetCurrentStep,
  }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    gapAnalysis: (...args: unknown[]) => mockGapAnalysisApi(...args),
  },
}));

vi.mock("@/lib/auth-store", () => ({
  useAuthStore: () => ({ user: { userId: "u1", githubUsername: "test", avatarUrl: "", hasApiKey: false }, isLoading: false }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ login: vi.fn(), logout: vi.fn() }),
}));

const sampleScores: ProficiencyScore[] = [
  {
    skillId: "react",
    skillName: "React",
    score: 72,
    confidence: 0.85,
    reasoning: "Good",
  },
];

const sampleGapAnalysis: GapAnalysis = {
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
};

import GapAnalysisPage from "./page";

beforeEach(() => {
  mockRouter.push.mockClear();
  mockSetGapAnalysis.mockClear();
  mockSetGapAnalysis.mockImplementation((data: GapAnalysis) => {
    mockState.gapAnalysis = data;
  });
  mockSetCurrentStep.mockClear();
  mockGapAnalysisApi.mockReset();
  mockState.scores = sampleScores;
  mockState.gapAnalysis = null;
});

describe("GapAnalysisPage", () => {
  it("redirects when no scores", () => {
    mockState.scores = [];
    render(<GapAnalysisPage />);
    expect(mockRouter.push).toHaveBeenCalledWith("/");
  });

  it("returns null when no scores", () => {
    mockState.scores = [];
    const { container } = render(<GapAnalysisPage />);
    expect(container.innerHTML).toBe("");
  });

  it("shows loading spinner during fetch", () => {
    mockGapAnalysisApi.mockImplementation(() => new Promise(() => {}));
    render(<GapAnalysisPage />);
    expect(screen.getByText("Analyzing skill gaps...")).toBeInTheDocument();
  });

  it("renders components on success", async () => {
    mockGapAnalysisApi.mockResolvedValueOnce(sampleGapAnalysis);
    render(<GapAnalysisPage />);

    await waitFor(() => {
      expect(screen.getByTestId("radar-chart")).toBeInTheDocument();
      expect(screen.getByTestId("gap-summary")).toBeInTheDocument();
      expect(screen.getByTestId("gap-card")).toBeInTheDocument();
    });
  });

  it("calls setGapAnalysis on success", async () => {
    mockGapAnalysisApi.mockResolvedValueOnce(sampleGapAnalysis);
    render(<GapAnalysisPage />);

    await waitFor(() => {
      expect(mockSetGapAnalysis).toHaveBeenCalledWith(sampleGapAnalysis);
    });
  });

  it("shows error message on failure", async () => {
    mockGapAnalysisApi.mockRejectedValueOnce(new Error("Network error"));
    render(<GapAnalysisPage />);
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("calls api again on retry", async () => {
    const user = userEvent.setup();
    mockGapAnalysisApi.mockRejectedValueOnce(new Error("First failure"));
    render(<GapAnalysisPage />);

    await waitFor(() => {
      expect(screen.getByText("First failure")).toBeInTheDocument();
    });

    mockGapAnalysisApi.mockResolvedValueOnce(sampleGapAnalysis);
    await user.click(screen.getByText("Retry"));

    await waitFor(() => {
      expect(mockSetGapAnalysis).toHaveBeenCalledWith(sampleGapAnalysis);
    });
  });

  it("shows retry failure message", async () => {
    const user = userEvent.setup();
    mockGapAnalysisApi.mockRejectedValueOnce(new Error("First failure"));
    render(<GapAnalysisPage />);

    await waitFor(() => {
      expect(screen.getByText("First failure")).toBeInTheDocument();
    });

    mockGapAnalysisApi.mockRejectedValueOnce(new Error("second"));
    await user.click(screen.getByText("Retry"));

    await waitFor(() => {
      expect(
        screen.getByText("Failed again. Please try later.")
      ).toBeInTheDocument();
    });
  });

  it("skips fetch when cached", () => {
    mockState.gapAnalysis = sampleGapAnalysis;
    render(<GapAnalysisPage />);
    expect(mockGapAnalysisApi).not.toHaveBeenCalled();
    expect(screen.getByTestId("radar-chart")).toBeInTheDocument();
  });

  it("continue navigates to learning plan", async () => {
    const user = userEvent.setup();
    mockState.gapAnalysis = sampleGapAnalysis;
    render(<GapAnalysisPage />);

    await user.click(screen.getByText("Generate Learning Plan"));

    expect(mockSetCurrentStep).toHaveBeenCalledWith(3);
    expect(mockRouter.push).toHaveBeenCalledWith("/learning-plan");
  });
});
