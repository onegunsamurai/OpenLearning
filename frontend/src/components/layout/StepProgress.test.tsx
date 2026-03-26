import { render, screen } from "@testing-library/react";
import { StepProgress } from "./StepProgress";

describe("StepProgress", () => {
  it("renders all step labels", () => {
    render(<StepProgress currentStep={0} />);
    expect(screen.getByText("Skills")).toBeInTheDocument();
    expect(screen.getByText("Assess")).toBeInTheDocument();
    expect(screen.getByText("Gaps")).toBeInTheDocument();
    expect(screen.getByText("Plan")).toBeInTheDocument();
  });

  it("makes completed steps clickable links", () => {
    render(<StepProgress currentStep={2} sessionId="session-123" />);
    // Steps 0 (Skills) and 1 (Assess) are completed — should be links
    const skillsLink = screen.getByText("Skills").closest("a");
    expect(skillsLink).toBeInTheDocument();
    expect(skillsLink).toHaveAttribute("href", "/");

    const assessLink = screen.getByText("Assess").closest("a");
    expect(assessLink).toBeInTheDocument();
    expect(assessLink).toHaveAttribute("href", "/assess?session=session-123");
  });

  it("does not make the current step a link", () => {
    render(<StepProgress currentStep={2} sessionId="session-123" />);
    const gapsLabel = screen.getByText("Gaps");
    expect(gapsLabel.closest("a")).not.toBeInTheDocument();
  });

  it("does not make future steps clickable", () => {
    render(<StepProgress currentStep={2} sessionId="session-123" />);
    const planLabel = screen.getByText("Plan");
    expect(planLabel.closest("a")).not.toBeInTheDocument();
  });

  it("builds hrefs without session param when sessionId is not provided", () => {
    render(<StepProgress currentStep={3} />);
    const gapsLink = screen.getByText("Gaps").closest("a");
    expect(gapsLink).toHaveAttribute("href", "/gap-analysis");
  });

  it("always links Skills step to / without session param", () => {
    render(<StepProgress currentStep={3} sessionId="session-456" />);
    const skillsLink = screen.getByText("Skills").closest("a");
    expect(skillsLink).toHaveAttribute("href", "/");
  });
});
