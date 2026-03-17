import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { DemoOnboardingDialog } from "./DemoOnboardingDialog";

describe("DemoOnboardingDialog", () => {
  it("renders dialog content when open", () => {
    render(<DemoOnboardingDialog open={true} onDismiss={vi.fn()} />);

    expect(screen.getByText("You're in Demo Mode")).toBeInTheDocument();
    expect(screen.getByText(/Responses are scripted/)).toBeInTheDocument();
    expect(screen.getByText(/No API key or account required/)).toBeInTheDocument();
    expect(screen.getByText(/sample gap analysis and learning plan/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Start Demo/ })).toBeInTheDocument();
  });

  it("calls onDismiss when CTA button is clicked", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    render(<DemoOnboardingDialog open={true} onDismiss={onDismiss} />);

    await user.click(screen.getByRole("button", { name: /Start Demo/ }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("does not render content when closed", () => {
    render(<DemoOnboardingDialog open={false} onDismiss={vi.fn()} />);

    expect(screen.queryByText("You're in Demo Mode")).not.toBeInTheDocument();
  });
});
