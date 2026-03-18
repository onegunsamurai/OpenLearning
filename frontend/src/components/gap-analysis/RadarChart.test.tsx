import { render } from "@testing-library/react";
import { vi } from "vitest";
import { transformGapData } from "./RadarChart";
import type { GapItem } from "@/lib/types";

const makeGap = (overrides: Partial<GapItem> = {}): GapItem => ({
  skillId: "s1",
  skillName: "React",
  currentLevel: 60,
  targetLevel: 80,
  gap: 20,
  priority: "high",
  recommendation: "Practice more",
  ...overrides,
});

describe("transformGapData", () => {
  it("maps skillName, currentLevel, targetLevel correctly", () => {
    const result = transformGapData([makeGap()]);
    expect(result).toEqual([
      { skill: "React", current: 60, target: 80 },
    ]);
  });

  it("preserves names with 12 or fewer characters", () => {
    const result = transformGapData([
      makeGap({ skillName: "123456789012" }),
    ]);
    expect(result[0].skill).toBe("123456789012");
  });

  it("truncates names longer than 12 characters", () => {
    const result = transformGapData([
      makeGap({ skillName: "1234567890123" }),
    ]);
    expect(result[0].skill).toBe("123456789012...");
  });

  it("returns empty array for empty input", () => {
    expect(transformGapData([])).toEqual([]);
  });

  it("preserves values within 0-100 range", () => {
    const result = transformGapData([
      makeGap({ currentLevel: 0, targetLevel: 100 }),
    ]);
    expect(result[0].current).toBe(0);
    expect(result[0].target).toBe(100);
  });

  it("includes both current and target in same data point", () => {
    const result = transformGapData([
      makeGap({ currentLevel: 30, targetLevel: 90 }),
    ]);
    expect(result[0]).toHaveProperty("current", 30);
    expect(result[0]).toHaveProperty("target", 90);
  });

  it("maps multiple items preserving order", () => {
    const result = transformGapData([
      makeGap({ skillName: "React", currentLevel: 60, targetLevel: 80 }),
      makeGap({ skillId: "s2", skillName: "TypeScript", currentLevel: 40, targetLevel: 70 }),
      makeGap({ skillId: "s3", skillName: "Node.js", currentLevel: 50, targetLevel: 90 }),
    ]);
    expect(result).toHaveLength(3);
    expect(result[0].skill).toBe("React");
    expect(result[1].skill).toBe("TypeScript");
    expect(result[2].skill).toBe("Node.js");
    expect(result[1].current).toBe(40);
    expect(result[2].target).toBe(90);
  });
});

// Mock recharts for component smoke tests
vi.mock("recharts", () => ({
  Radar: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="radar">{children}</div>
  ),
  RadarChart: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="radar-chart">{children}</div>
  ),
  PolarGrid: () => <div data-testid="polar-grid" />,
  PolarAngleAxis: () => <div data-testid="polar-angle-axis" />,
  PolarRadiusAxis: () => <div data-testid="polar-radius-axis" />,
  ResponsiveContainer: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  Legend: () => <div data-testid="legend" />,
}));

describe("RadarChart component", () => {
  // Import after mock is set up
  let RadarChart: typeof import("./RadarChart").RadarChart;

  beforeAll(async () => {
    const mod = await import("./RadarChart");
    RadarChart = mod.RadarChart;
  });

  it("renders without crashing with valid data", () => {
    const { getByTestId } = render(
      <RadarChart gaps={[makeGap(), makeGap({ skillId: "s2", skillName: "TypeScript" })]} />
    );
    expect(getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("renders without crashing with empty array", () => {
    const { getByTestId } = render(<RadarChart gaps={[]} />);
    expect(getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("renders chart sub-components", () => {
    const { getByTestId } = render(
      <RadarChart gaps={[makeGap()]} />
    );
    expect(getByTestId("responsive-container")).toBeInTheDocument();
    expect(getByTestId("radar-chart")).toBeInTheDocument();
    expect(getByTestId("polar-grid")).toBeInTheDocument();
    expect(getByTestId("legend")).toBeInTheDocument();
  });
});
