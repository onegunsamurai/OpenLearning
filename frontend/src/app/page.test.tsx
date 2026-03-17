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
  },
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

  it("renders bottom bar 'Try Demo' link pointing to /demo/assess", () => {
    render(<OnboardingPage />);
    const links = screen.getAllByRole("link", { name: /Try Demo/i });
    const bottomBarLink = links.find(
      (link) => link.textContent?.trim() === "Try Demo"
    );
    expect(bottomBarLink).toBeInTheDocument();
    expect(bottomBarLink).toHaveAttribute("href", "/demo/assess");
  });
});
