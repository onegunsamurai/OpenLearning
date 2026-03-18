import { render, screen } from "@testing-library/react";
import { GapSummary } from "./GapSummary";

// Make requestAnimationFrame run callbacks synchronously for deterministic tests
beforeEach(() => {
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
    cb(performance.now() + 2000);
    return 0;
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("GapSummary", () => {
  it("renders readiness percentage", () => {
    render(<GapSummary readiness={75} summary="Good progress" />);
    expect(screen.getByText(/75%/)).toBeInTheDocument();
  });

  it("renders summary text", () => {
    render(<GapSummary readiness={50} summary="Moderate readiness with gaps" />);
    expect(
      screen.getByText("Moderate readiness with gaps")
    ).toBeInTheDocument();
  });

  it("applies green color at 75 or above", () => {
    const { container } = render(
      <GapSummary readiness={75} summary="Good" />
    );
    const spans = container.querySelectorAll("span");
    const percentSpan = Array.from(spans).find((s) =>
      s.textContent?.includes("75%")
    );
    expect(percentSpan?.className).toContain("text-green-400");
  });

  it("applies yellow color between 50 and 74", () => {
    const { container } = render(
      <GapSummary readiness={60} summary="Moderate" />
    );
    const spans = container.querySelectorAll("span");
    const percentSpan = Array.from(spans).find((s) =>
      s.textContent?.includes("60%")
    );
    expect(percentSpan?.className).toContain("text-yellow-400");
  });

  it("applies red color below 50", () => {
    const { container } = render(
      <GapSummary readiness={30} summary="Needs work" />
    );
    const spans = container.querySelectorAll("span");
    const percentSpan = Array.from(spans).find((s) =>
      s.textContent?.includes("30%")
    );
    expect(percentSpan?.className).toContain("text-red-400");
  });

  it("renders overall readiness heading", () => {
    render(<GapSummary readiness={50} summary="Test" />);
    expect(screen.getByText("Overall Readiness")).toBeInTheDocument();
  });
});
