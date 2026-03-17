import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

import DemoAssessPage from "./page";
import { DEMO_ASSESSMENT_START } from "@/lib/demo/fixtures";

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  // jsdom doesn't implement scrollIntoView
  Element.prototype.scrollIntoView = vi.fn();
});

describe("DemoAssessPage", () => {
  it("shows onboarding dialog on first visit", () => {
    render(<DemoAssessPage />);

    expect(screen.getByText("You're in Demo Mode")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Start Demo/ })).toBeInTheDocument();
  });

  it("skips dialog if sessionStorage has demo-onboarding-seen", async () => {
    sessionStorage.setItem("demo-onboarding-seen", "true");
    render(<DemoAssessPage />);

    expect(screen.queryByText("You're in Demo Mode")).not.toBeInTheDocument();

    // Chat should auto-start
    await waitFor(() => {
      expect(
        screen.getByText(DEMO_ASSESSMENT_START.question)
      ).toBeInTheDocument();
    });
  });

  it("does not auto-start chat while dialog is open", async () => {
    render(<DemoAssessPage />);

    // Dialog is visible
    expect(screen.getByText("You're in Demo Mode")).toBeInTheDocument();

    // The first demo question should NOT appear yet
    expect(
      screen.queryByText(DEMO_ASSESSMENT_START.question)
    ).not.toBeInTheDocument();
  });

  it("starts chat after dialog is dismissed", async () => {
    const user = userEvent.setup();
    render(<DemoAssessPage />);

    // Dismiss the dialog
    await user.click(screen.getByRole("button", { name: /Start Demo/ }));

    // Chat should start
    await waitFor(() => {
      expect(
        screen.getByText(DEMO_ASSESSMENT_START.question)
      ).toBeInTheDocument();
    });

    // sessionStorage should be set
    expect(sessionStorage.getItem("demo-onboarding-seen")).toBe("true");
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
    sessionStorage.setItem("demo-onboarding-seen", "true");
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
    sessionStorage.setItem("demo-onboarding-seen", "true");
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
