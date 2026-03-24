import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import type { AssessmentProgress } from "@/hooks/useAssessmentChat";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => ({ get: () => null }),
}));

const mockSendMessage = vi.fn();
const mockInitialiseChat = vi.fn();
let mockProgress: AssessmentProgress | null = null;

vi.mock("@/hooks/useAssessmentChat", () => ({
  useAssessmentChat: () => ({
    messages: [{ id: "1", role: "assistant", content: "Hello" }],
    sendMessage: mockSendMessage,
    status: "ready",
    error: null,
    initialiseChat: mockInitialiseChat,
    sessionId: "test-session",
    progress: mockProgress,
  }),
}));

vi.mock("@/lib/store", () => ({
  useAppStore: () => ({
    selectedSkillIds: ["skill-1"],
    setCurrentStep: vi.fn(),
    setAssessmentSessionId: vi.fn(),
    targetLevel: "intermediate",
    selectedRoleId: null,
  }),
}));

vi.mock("@/lib/auth-store", () => ({
  useAuthStore: () => ({ user: { userId: "u1", displayName: "test", avatarUrl: "", hasApiKey: true, email: null }, isLoading: false, setUser: vi.fn() }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ login: vi.fn(), logout: vi.fn() }),
}));

vi.mock("@/components/layout/PageShell", () => ({
  PageShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/lib/api", () => ({
  api: {
    authMe: vi.fn().mockResolvedValue({ userId: "u1", displayName: "test", avatarUrl: "", hasApiKey: false, email: null }),
    authGetApiKey: vi.fn().mockRejectedValue(new Error("No key")),
    authValidateKey: vi.fn(),
    authSetApiKey: vi.fn(),
    authDeleteApiKey: vi.fn(),
  },
}));

import AssessPage from "./page";

beforeEach(() => {
  vi.clearAllMocks();
  mockProgress = null;
  Element.prototype.scrollIntoView = vi.fn();
});

describe("AssessPage progress bar", () => {
  it("shows numeric percentage for normal assessment progress", () => {
    mockProgress = { type: "assessment", totalQuestions: 9, maxQuestions: 25 };
    render(<AssessPage />);

    // Question 10 of ~25 → 40%
    expect(screen.getByText("Question 10 of ~25")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
  });

  it("shows 'Almost done' when assessment overflows maxQuestions", () => {
    mockProgress = { type: "assessment", totalQuestions: 25, maxQuestions: 25 };
    render(<AssessPage />);

    // Question 26 of ~25 → 104%, should show "Almost done" instead
    expect(screen.getByText("Question 26 of ~25")).toBeInTheDocument();
    expect(screen.getByText("Almost done")).toBeInTheDocument();
    expect(screen.queryByText(/104%/)).not.toBeInTheDocument();

    // Progress bar indicator style should be capped at 95%
    const indicator = document.querySelector("[data-slot='progress-indicator']");
    expect(indicator).toHaveStyle({ transform: `translateX(-${100 - 95}%)` });
  });

  it("shows 'Almost done' at exactly 95% threshold", () => {
    // totalQuestions=22, maxQuestions=24 → (23/24)*100 ≈ 95.83% → >= 95
    mockProgress = { type: "assessment", totalQuestions: 22, maxQuestions: 24 };
    render(<AssessPage />);

    expect(screen.getByText("Almost done")).toBeInTheDocument();
    expect(screen.queryByText(/96%/)).not.toBeInTheDocument();

    const indicator = document.querySelector("[data-slot='progress-indicator']");
    expect(indicator).toHaveStyle({ transform: `translateX(-${100 - 95}%)` });
  });

  it("shows numeric percentage for calibration progress (unaffected)", () => {
    mockProgress = { type: "calibration", step: 2, totalSteps: 3 };
    render(<AssessPage />);

    expect(screen.getByText("Calibration: Step 2 of 3")).toBeInTheDocument();
    expect(screen.getByText("67%")).toBeInTheDocument();
    expect(screen.queryByText("Almost done")).not.toBeInTheDocument();
  });
});
