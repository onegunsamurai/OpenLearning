import { render, screen } from "@testing-library/react";
import { QualityBadge } from "./quality-badge";

describe("QualityBadge", () => {
  it("shows 'High Quality' for score >= 0.8 with no flag", () => {
    render(<QualityBadge qualityScore={0.85} qualityFlag={null} />);
    expect(screen.getByText("High Quality")).toBeInTheDocument();
  });

  it("shows 'Acceptable' for score >= 0.6 and < 0.8 with no flag", () => {
    render(<QualityBadge qualityScore={0.7} qualityFlag={null} />);
    expect(screen.getByText("Acceptable")).toBeInTheDocument();
  });

  it("shows 'Needs Review' for score < 0.6 with no flag", () => {
    render(<QualityBadge qualityScore={0.5} qualityFlag={null} />);
    expect(screen.getByText("Needs Review")).toBeInTheDocument();
  });

  it("shows 'Review Suggested' when qualityFlag is set regardless of score", () => {
    render(
      <QualityBadge
        qualityScore={0.95}
        qualityFlag="max_iterations_reached"
      />
    );
    expect(screen.getByText("Review Suggested")).toBeInTheDocument();
  });

  it("does not display raw flag string", () => {
    render(
      <QualityBadge
        qualityScore={0.9}
        qualityFlag="max_iterations_reached"
      />
    );
    expect(
      screen.queryByText("max_iterations_reached")
    ).not.toBeInTheDocument();
  });

  it("boundary: score exactly 0.8 shows 'High Quality'", () => {
    render(<QualityBadge qualityScore={0.8} qualityFlag={null} />);
    expect(screen.getByText("High Quality")).toBeInTheDocument();
  });

  it("boundary: score exactly 0.6 shows 'Acceptable'", () => {
    render(<QualityBadge qualityScore={0.6} qualityFlag={null} />);
    expect(screen.getByText("Acceptable")).toBeInTheDocument();
  });

  it("boundary: score 0.0 shows 'Needs Review'", () => {
    render(<QualityBadge qualityScore={0.0} qualityFlag={null} />);
    expect(screen.getByText("Needs Review")).toBeInTheDocument();
  });

  it("boundary: score 1.0 shows 'High Quality'", () => {
    render(<QualityBadge qualityScore={1.0} qualityFlag={null} />);
    expect(screen.getByText("High Quality")).toBeInTheDocument();
  });
});
