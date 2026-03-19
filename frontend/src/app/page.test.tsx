import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/lib/store", () => ({
  useAppStore: () => ({
    selectedSkillIds: [],
    toggleSkill: vi.fn(),
    setSelectedSkillIds: vi.fn(),
    setCurrentStep: vi.fn(),
    selectedRoleId: null,
    setSelectedRoleId: vi.fn(),
    roleSkillIds: [],
    setRoleSkillIds: vi.fn(),
    targetLevel: "mid",
    setTargetLevel: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    getSkills: vi.fn().mockResolvedValue({ skills: [], categories: [] }),
    getRoles: vi.fn().mockResolvedValue([]),
    authMe: vi.fn().mockRejectedValue(new Error("not authenticated")),
  },
}));

vi.mock("@/lib/auth-store", () => ({
  useAuthStore: () => ({ user: null, isLoading: false }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ login: vi.fn(), logout: vi.fn() }),
}));

import OnboardingPage from "./page";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("OnboardingPage", () => {
  it("renders hero 'Try Interactive Demo' link pointing to /demo/assess", () => {
    render(<OnboardingPage />);
    const heroLink = screen.getByRole("link", { name: /Try Interactive Demo/i });
    expect(heroLink).toBeInTheDocument();
    expect(heroLink).toHaveAttribute("href", "/demo/assess");
  });

  it("renders 'No signup required' subtext", () => {
    render(<OnboardingPage />);
    expect(screen.getByText(/No signup required/i)).toBeInTheDocument();
  });

  it("does not render 'Try Demo' link in bottom bar", () => {
    render(<OnboardingPage />);
    const links = screen.queryAllByRole("link", { name: /Try Demo/i });
    const bottomBarLink = links.find(
      (link) => link.textContent?.trim() === "Try Demo"
    );
    expect(bottomBarLink).toBeUndefined();
  });
});
