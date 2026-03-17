import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi } from "vitest";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

import DemoAssessPage from "./page";
import { DEMO_ASSESSMENT_START } from "@/lib/demo/fixtures";

beforeEach(() => {
  vi.clearAllMocks();
  // jsdom doesn't implement scrollIntoView
  Element.prototype.scrollIntoView = vi.fn();
});

describe("DemoAssessPage", () => {
  it("renders first demo question on mount", async () => {
    render(<DemoAssessPage />);

    await waitFor(() => {
      expect(
        screen.getByText(DEMO_ASSESSMENT_START.question)
      ).toBeInTheDocument();
    });
  });

  it("shows demo badge", () => {
    render(<DemoAssessPage />);
    expect(screen.getByText("Demo")).toBeInTheDocument();
  });

  it("shows demo header text", () => {
    render(<DemoAssessPage />);
    expect(screen.getByText("Demo Assessment")).toBeInTheDocument();
  });

  it("renders user message after form submission", async () => {
    render(<DemoAssessPage />);

    await waitFor(() => {
      expect(
        screen.getByText(DEMO_ASSESSMENT_START.question)
      ).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/Type anything/i);
    fireEvent.change(textarea, { target: { value: "My test answer" } });

    // Submit via form
    const form = textarea.closest("form")!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(screen.getByText("My test answer")).toBeInTheDocument();
    });
  });

  it("shows progress bar", async () => {
    render(<DemoAssessPage />);

    await waitFor(() => {
      expect(
        screen.getByText(DEMO_ASSESSMENT_START.question)
      ).toBeInTheDocument();
    });

    // Progress bar should show calibration state
    expect(screen.getByText(/Calibration/)).toBeInTheDocument();
  });
});
