import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock recharts to avoid canvas issues in jsdom
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => children,
  RadarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="radar-chart">{children}</div>,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  PolarRadiusAxis: () => null,
  Radar: () => null,
  Legend: () => null,
  Tooltip: () => null,
}));

import DemoReportPage from "./page";
import { DEMO_GAP_ANALYSIS, DEMO_LEARNING_PLAN, DEMO_PROFICIENCY_SCORES } from "@/lib/demo/fixtures";

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
});

describe("DemoReportPage", () => {
  it("renders proficiency scores from fixtures", () => {
    render(<DemoReportPage />);

    // Proficiency scores section exists
    expect(screen.getByText("Proficiency Scores")).toBeInTheDocument();
    // Each score value is rendered
    for (const score of DEMO_PROFICIENCY_SCORES) {
      expect(screen.getAllByText(score.skillName).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(`${score.score}%`).length).toBeGreaterThanOrEqual(1);
    }
  });

  it("renders gap analysis data", () => {
    render(<DemoReportPage />);

    expect(screen.getByText("Skill Gap Breakdown")).toBeInTheDocument();
    for (const gap of DEMO_GAP_ANALYSIS.gaps) {
      expect(screen.getAllByText(gap.skillName).length).toBeGreaterThanOrEqual(1);
    }
  });

  it("renders radar chart", () => {
    render(<DemoReportPage />);
    expect(screen.getByTestId("radar-chart")).toBeInTheDocument();
  });

  it("shows demo badge", () => {
    render(<DemoReportPage />);
    expect(screen.getByText("Demo")).toBeInTheDocument();
  });

  it("switches to learning plan tab", async () => {
    const user = userEvent.setup();
    render(<DemoReportPage />);

    // Click the Learning Plan tab button
    const tabButtons = screen.getAllByRole("button", { name: /Learning Plan/i });
    await user.click(tabButtons[0]);

    expect(screen.getByText(DEMO_LEARNING_PLAN.title)).toBeInTheDocument();
  });

  it("renders learning plan phases", async () => {
    const user = userEvent.setup();
    render(<DemoReportPage />);

    const tabButtons = screen.getAllByRole("button", { name: /Learning Plan/i });
    await user.click(tabButtons[0]);

    for (const phase of DEMO_LEARNING_PLAN.phases) {
      // Phase names may appear in sidebar buttons and timeline
      expect(screen.getAllByText(phase.name).length).toBeGreaterThanOrEqual(1);
    }
  });

  it("download button triggers Blob download", async () => {
    const user = userEvent.setup();

    const mockObjectURL = "blob:http://localhost/mock";
    const createObjectURL = vi.fn().mockReturnValue(mockObjectURL);
    const revokeObjectURL = vi.fn();
    Object.defineProperty(window, "URL", {
      value: { createObjectURL, revokeObjectURL },
      writable: true,
    });

    const clickSpy = vi.fn();
    const createElementOrig = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      if (tag === "a") {
        const el = createElementOrig(tag) as HTMLAnchorElement;
        el.click = clickSpy;
        return el;
      }
      return createElementOrig(tag);
    });

    render(<DemoReportPage />);

    await user.click(screen.getByRole("button", { name: /Download Report/i }));

    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith(mockObjectURL);
  });

  it("Start Over clears sessionStorage and navigates to /demo/assess", async () => {
    const user = userEvent.setup();
    sessionStorage.setItem("demo-onboarding-seen", "true");
    render(<DemoReportPage />);

    await user.click(screen.getByRole("button", { name: /Start Over/i }));
    expect(sessionStorage.getItem("demo-onboarding-seen")).toBeNull();
    expect(mockPush).toHaveBeenCalledWith("/demo/assess");
  });

  it("Try the Real Thing navigates to /", async () => {
    const user = userEvent.setup();
    render(<DemoReportPage />);

    await user.click(screen.getByRole("button", { name: /Try the Real Thing/i }));
    expect(mockPush).toHaveBeenCalledWith("/");
  });
});
