import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { NoGapsSuccess } from "./no-gaps-success";
import type { ProficiencyScore } from "@/lib/types";

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
  targetLevel: "mid",
  onStartOver: vi.fn(),
};

describe("NoGapsSuccess", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders trophy and heading", () => {
    render(<NoGapsSuccess {...defaultProps} />);
    expect(
      screen.getByText("No Learning Plan Needed!")
    ).toBeInTheDocument();
  });

  it("shows level name in description", () => {
    render(<NoGapsSuccess {...defaultProps} targetLevel="senior" />);
    expect(
      screen.getByText(/Senior level/)
    ).toBeInTheDocument();
  });

  it("renders all skill scores without reasoning", () => {
    render(<NoGapsSuccess {...defaultProps} />);
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByText("95%")).toBeInTheDocument();
    expect(screen.getByText("88%")).toBeInTheDocument();
    // Reasoning should be hidden
    expect(screen.queryByText("Excellent")).not.toBeInTheDocument();
    expect(screen.queryByText("Very good")).not.toBeInTheDocument();
  });

  it("shows skill count", () => {
    render(<NoGapsSuccess {...defaultProps} />);
    expect(screen.getByText("2 skills verified")).toBeInTheDocument();
  });

  it("handles singular skill count", () => {
    render(<NoGapsSuccess {...defaultProps} scores={[mockScores[0]]} />);
    expect(screen.getByText("1 skill verified")).toBeInTheDocument();
  });

  it("hides scores section when scores array is empty", () => {
    render(<NoGapsSuccess {...defaultProps} scores={[]} />);
    expect(screen.queryByText("Skills Verified")).not.toBeInTheDocument();
  });

  it("shows 'Try a Harder Level' for non-max levels", () => {
    render(<NoGapsSuccess {...defaultProps} targetLevel="mid" />);
    expect(screen.getByText("Try a Harder Level")).toBeInTheDocument();
  });

  it("shows 'Add More Skills' for staff level", () => {
    render(<NoGapsSuccess {...defaultProps} targetLevel="staff" />);
    expect(screen.getByText("Add More Skills")).toBeInTheDocument();
  });

  it("calls onStartOver when primary CTA clicked", async () => {
    const user = userEvent.setup();
    const onStartOver = vi.fn();
    render(<NoGapsSuccess {...defaultProps} onStartOver={onStartOver} />);

    await user.click(screen.getByText("Try a Harder Level"));
    expect(onStartOver).toHaveBeenCalledTimes(1);
  });

  it("calls onStartOver when secondary CTA clicked", async () => {
    const user = userEvent.setup();
    const onStartOver = vi.fn();
    render(<NoGapsSuccess {...defaultProps} onStartOver={onStartOver} />);

    await user.click(screen.getByText("Start New Assessment"));
    expect(onStartOver).toHaveBeenCalledTimes(1);
  });

  it("falls back to raw targetLevel for unknown levels", () => {
    render(<NoGapsSuccess {...defaultProps} targetLevel="expert" />);
    expect(screen.getByText(/expert level/)).toBeInTheDocument();
  });

  it("shows generic copy when targetLevel is empty", () => {
    render(<NoGapsSuccess {...defaultProps} targetLevel="" />);
    expect(
      screen.getByText(/demonstrated mastery across all assessed skills/)
    ).toBeInTheDocument();
    expect(screen.queryByText(/at the {2}level/)).not.toBeInTheDocument();
  });
});
