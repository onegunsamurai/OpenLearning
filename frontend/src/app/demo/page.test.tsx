import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

import DemoOnboardingPage from "./page";
import { DEMO_SKILLS } from "@/lib/demo/fixtures";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("DemoOnboardingPage", () => {
  it("renders fixture skills", () => {
    render(<DemoOnboardingPage />);

    for (const skill of DEMO_SKILLS.skills) {
      expect(screen.getByText(skill.name)).toBeInTheDocument();
    }
  });

  it("shows demo badge in header", () => {
    render(<DemoOnboardingPage />);
    expect(screen.getByText("Demo")).toBeInTheDocument();
  });

  it("disables Start Assessment when no skills selected", () => {
    render(<DemoOnboardingPage />);
    const button = screen.getByRole("button", { name: /Start Assessment/i });
    expect(button).toBeDisabled();
  });

  it("enables Start Assessment after selecting a skill", async () => {
    const user = userEvent.setup();
    render(<DemoOnboardingPage />);

    const skillButton = screen.getByText(DEMO_SKILLS.skills[0].name);
    await user.click(skillButton);

    const startButton = screen.getByRole("button", { name: /Start Assessment/i });
    expect(startButton).toBeEnabled();
  });

  it("navigates to /demo/assess on Start Assessment", async () => {
    const user = userEvent.setup();
    render(<DemoOnboardingPage />);

    // Select a skill
    const skillButton = screen.getByText(DEMO_SKILLS.skills[0].name);
    await user.click(skillButton);

    // Click start
    const startButton = screen.getByRole("button", { name: /Start Assessment/i });
    await user.click(startButton);

    expect(mockPush).toHaveBeenCalledWith("/demo/assess");
  });

  it("shows skill count when skills are selected", async () => {
    const user = userEvent.setup();
    render(<DemoOnboardingPage />);

    const skillButton = screen.getByText(DEMO_SKILLS.skills[0].name);
    await user.click(skillButton);

    expect(screen.getByText(/skill selected/i)).toBeInTheDocument();
  });
});
