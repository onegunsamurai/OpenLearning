import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { NoGapsHero } from "./no-gaps-hero";
import type { ProficiencyScore } from "@/lib/types";

vi.mock("@/components/gap-analysis/GapSummary", () => ({
  GapSummary: ({ readiness }: { readiness: number }) => (
    <div data-testid="gap-summary">Readiness: {readiness}%</div>
  ),
}));

const mockScores: ProficiencyScore[] = [
  {
    skillId: "react",
    skillName: "React",
    score: 95,
    confidence: 0.9,
    reasoning: "Excellent",
  },
  {
    skillId: "ts",
    skillName: "TypeScript",
    score: 88,
    confidence: 0.85,
    reasoning: "Very good",
  },
];

const defaultProps = {
  scores: mockScores,
  overallReadiness: 100,
  summary: "No significant gaps identified. Great job!",
  targetLevel: "mid",
  onStartOver: vi.fn(),
  onContinue: vi.fn(),
};

describe("NoGapsHero", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders trophy icon and congratulations heading", () => {
    render(<NoGapsHero {...defaultProps} />);
    expect(
      screen.getByText("Outstanding Performance!")
    ).toBeInTheDocument();
  });

  it("renders GapSummary with readiness", () => {
    render(<NoGapsHero {...defaultProps} />);
    expect(screen.getByTestId("gap-summary")).toBeInTheDocument();
    expect(screen.getByText("Readiness: 100%")).toBeInTheDocument();
  });

  it("renders all skill score cards", () => {
    render(<NoGapsHero {...defaultProps} />);
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByText("95%")).toBeInTheDocument();
    expect(screen.getByText("88%")).toBeInTheDocument();
  });

  it("shows 'Try a Harder Level' for non-max levels", () => {
    render(<NoGapsHero {...defaultProps} targetLevel="mid" />);
    expect(screen.getByText("Try a Harder Level")).toBeInTheDocument();
  });

  it("shows 'Add More Skills' for staff level", () => {
    render(<NoGapsHero {...defaultProps} targetLevel="staff" />);
    expect(screen.getByText("Add More Skills")).toBeInTheDocument();
  });

  it("shows 'Try a Harder Level' for empty targetLevel (defaults to non-max)", () => {
    render(<NoGapsHero {...defaultProps} targetLevel="" />);
    expect(screen.getByText("Try a Harder Level")).toBeInTheDocument();
  });

  it("calls onStartOver when primary CTA clicked", async () => {
    const user = userEvent.setup();
    const onStartOver = vi.fn();
    render(<NoGapsHero {...defaultProps} onStartOver={onStartOver} />);

    await user.click(screen.getByText("Try a Harder Level"));
    expect(onStartOver).toHaveBeenCalledTimes(1);
  });

  it("calls onContinue when 'View Learning Plan' clicked", async () => {
    const user = userEvent.setup();
    const onContinue = vi.fn();
    render(<NoGapsHero {...defaultProps} onContinue={onContinue} />);

    await user.click(screen.getByText("View Learning Plan"));
    expect(onContinue).toHaveBeenCalledTimes(1);
  });

  it("renders with empty scores array", () => {
    render(<NoGapsHero {...defaultProps} scores={[]} />);
    expect(
      screen.getByText("Outstanding Performance!")
    ).toBeInTheDocument();
    expect(screen.getByText("Your Skill Scores")).toBeInTheDocument();
  });
});
