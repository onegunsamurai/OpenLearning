import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const { mockOpenApiKeySetup } = vi.hoisted(() => {
  return {
    mockOpenApiKeySetup: vi.fn(),
  };
});

vi.mock("@/components/layout/PageShell", () => ({
  useApiKeySetupContext: () => ({ openApiKeySetup: mockOpenApiKeySetup }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/api")>();
  return { ApiError: mod.ApiError };
});

import { ApiError } from "@/lib/api";
import { ApiErrorDisplay } from "./api-error-display";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ApiErrorDisplay", () => {
  it("renders connection error for TypeError (network failure)", () => {
    render(<ApiErrorDisplay error={new TypeError("Failed to fetch")} />);
    expect(screen.getByText("Connection Error")).toBeInTheDocument();
    expect(
      screen.getByText(/Cannot reach the server/)
    ).toBeInTheDocument();
  });

  it("renders generic error with message for non-TypeError, non-ApiError", () => {
    render(<ApiErrorDisplay error={new Error("Something unexpected")} />);
    expect(screen.getByText("Something Went Wrong")).toBeInTheDocument();
    expect(screen.getByText("Something unexpected")).toBeInTheDocument();
  });

  it("renders 401 error with Update API Key button", () => {
    const error = new ApiError("Your API key is invalid or has been revoked.", 401);
    render(<ApiErrorDisplay error={error} onRetry={vi.fn()} />);
    expect(screen.getByText("Invalid API Key")).toBeInTheDocument();
    expect(screen.getByText("Update API Key")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("calls openApiKeySetup when Update API Key is clicked", async () => {
    const user = userEvent.setup();
    const error = new ApiError("Invalid key", 401);
    render(<ApiErrorDisplay error={error} />);

    await user.click(screen.getByText("Update API Key"));
    expect(mockOpenApiKeySetup).toHaveBeenCalled();
  });

  it("renders 429 error with countdown", () => {
    vi.useFakeTimers();
    const error = new ApiError("Rate limit reached", 429, 10);
    render(<ApiErrorDisplay error={error} onRetry={vi.fn()} />);

    expect(screen.getByText("Rate Limited")).toBeInTheDocument();
    expect(screen.getByText("Auto-retrying in 10s...")).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("countdown decrements and auto-retries", () => {
    vi.useFakeTimers();
    const onRetry = vi.fn();
    const error = new ApiError("Rate limit reached", 429, 3);
    render(<ApiErrorDisplay error={error} onRetry={onRetry} />);

    expect(screen.getByText("Auto-retrying in 3s...")).toBeInTheDocument();

    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.getByText("Auto-retrying in 2s...")).toBeInTheDocument();

    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.getByText("Auto-retrying in 1s...")).toBeInTheDocument();

    act(() => { vi.advanceTimersByTime(1000); });
    expect(onRetry).toHaveBeenCalled();

    vi.useRealTimers();
  });

  it("disables retry button during countdown for 429", () => {
    vi.useFakeTimers();
    const error = new ApiError("Rate limited", 429, 5);
    render(<ApiErrorDisplay error={error} onRetry={vi.fn()} />);

    const retryBtn = screen.getByText("Retry").closest("button");
    expect(retryBtn).toBeDisabled();

    vi.useRealTimers();
  });

  it("renders 502 error", () => {
    const error = new ApiError("Unable to reach the AI service.", 502);
    render(<ApiErrorDisplay error={error} onRetry={vi.fn()} />);
    expect(screen.getByText("Service Unavailable")).toBeInTheDocument();
  });

  it("renders 504 error", () => {
    const error = new ApiError("The AI service timed out.", 504);
    render(<ApiErrorDisplay error={error} onRetry={vi.fn()} />);
    expect(screen.getByText("Service Unavailable")).toBeInTheDocument();
  });

  it("renders 500 error", () => {
    const error = new ApiError("Something went wrong", 500);
    render(<ApiErrorDisplay error={error} onRetry={vi.fn()} />);
    expect(screen.getByText("Something Went Wrong")).toBeInTheDocument();
  });

  it("calls onRetry when Retry button is clicked", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    const error = new ApiError("Server error", 500);
    render(<ApiErrorDisplay error={error} onRetry={onRetry} />);

    await user.click(screen.getByText("Retry"));
    expect(onRetry).toHaveBeenCalled();
  });

  it("does not render Retry button when onRetry is not provided", () => {
    const error = new ApiError("Server error", 500);
    render(<ApiErrorDisplay error={error} />);
    expect(screen.queryByText("Retry")).not.toBeInTheDocument();
  });

  it("does not show Update API Key for non-401 errors", () => {
    const error = new ApiError("Timeout", 504);
    render(<ApiErrorDisplay error={error} onRetry={vi.fn()} />);
    expect(screen.queryByText("Update API Key")).not.toBeInTheDocument();
  });
});
