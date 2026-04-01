import { render, screen } from "@testing-library/react";
import { SkillScoreCard } from "./skill-score-card";
import type { ProficiencyScore } from "@/lib/types";

const mockScore: ProficiencyScore = {
  skillId: "react",
  skillName: "React",
  score: 85,
  confidence: 0.9,
  reasoning: "Strong understanding of hooks and component patterns",
};

describe("SkillScoreCard", () => {
  it("renders skill name and score", () => {
    render(<SkillScoreCard score={mockScore} index={0} />);
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("renders reasoning by default", () => {
    render(<SkillScoreCard score={mockScore} index={0} />);
    expect(
      screen.getByText("Strong understanding of hooks and component patterns")
    ).toBeInTheDocument();
  });

  it("hides reasoning when showReasoning is false", () => {
    render(
      <SkillScoreCard score={mockScore} index={0} showReasoning={false} />
    );
    expect(
      screen.queryByText(
        "Strong understanding of hooks and component patterns"
      )
    ).not.toBeInTheDocument();
  });

  it("renders progress bar with accessible label", () => {
    render(<SkillScoreCard score={mockScore} index={0} />);
    const progressBar = screen.getByRole("progressbar", {
      name: /React proficiency: 85%/i,
    });
    expect(progressBar).toBeInTheDocument();
  });

  it("renders with zero score", () => {
    const zeroScore = { ...mockScore, score: 0, skillName: "Go" };
    render(<SkillScoreCard score={zeroScore} index={0} />);
    expect(screen.getByText("Go")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
  });
});
