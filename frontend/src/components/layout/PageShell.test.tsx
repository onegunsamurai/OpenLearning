import { render, screen } from "@testing-library/react";
import { useAuthStore } from "@/lib/auth-store";
import type { AuthMeResponse } from "@/lib/types";

import { PageShell } from "./PageShell";

// Mock useAuth hook to prevent actual API calls
vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

const mockUser: AuthMeResponse = {
  userId: "user-1",
  githubUsername: "testuser",
  avatarUrl: "https://github.com/avatar.png",
  hasApiKey: false,
};

describe("PageShell", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isLoading: false });
  });

  it("does not render 'Try Demo' link in header", () => {
    render(
      <PageShell currentStep={0}>
        <div>content</div>
      </PageShell>
    );
    expect(screen.queryByRole("link", { name: /Try Demo/i })).not.toBeInTheDocument();
  });

  it("hides stepper when currentStep is not provided", () => {
    render(
      <PageShell>
        <div>content</div>
      </PageShell>
    );
    // StepProgress labels should not appear when currentStep is undefined
    expect(screen.queryByText("Skills")).not.toBeInTheDocument();
    expect(screen.queryByText("Assess")).not.toBeInTheDocument();
  });

  it("renders 'Demo' badge when isDemo is true", () => {
    render(
      <PageShell currentStep={0} isDemo>
        <div>content</div>
      </PageShell>
    );
    expect(screen.getByText("Demo")).toBeInTheDocument();
  });

  it("shows sign-in button when unauthenticated", () => {
    useAuthStore.setState({ user: null, isLoading: false });
    render(
      <PageShell currentStep={0}>
        <div>content</div>
      </PageShell>
    );
    expect(screen.getByText("Sign in with GitHub")).toBeInTheDocument();
  });

  it("shows username when authenticated", () => {
    useAuthStore.setState({ user: mockUser, isLoading: false });
    render(
      <PageShell currentStep={0}>
        <div>content</div>
      </PageShell>
    );
    expect(screen.getByText("testuser")).toBeInTheDocument();
    expect(screen.queryByText("Sign in with GitHub")).not.toBeInTheDocument();
  });

  it("shows loading skeleton while auth is resolving", () => {
    useAuthStore.setState({ user: null, isLoading: true });
    const { container } = render(
      <PageShell currentStep={0}>
        <div>content</div>
      </PageShell>
    );
    // The skeleton has animate-pulse class
    const skeleton = container.querySelector(".animate-pulse");
    expect(skeleton).toBeInTheDocument();
    expect(screen.queryByText("Sign in with GitHub")).not.toBeInTheDocument();
    expect(screen.queryByText("testuser")).not.toBeInTheDocument();
  });

  it("does not show auth UI in demo mode", () => {
    useAuthStore.setState({ user: null, isLoading: false });
    render(
      <PageShell currentStep={0} isDemo>
        <div>content</div>
      </PageShell>
    );
    expect(screen.queryByText("Sign in with GitHub")).not.toBeInTheDocument();
  });
});
