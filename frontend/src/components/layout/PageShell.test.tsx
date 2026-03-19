import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

// Mock api module
vi.mock("@/lib/api", () => ({
  api: {
    authMe: vi.fn().mockResolvedValue({
      userId: "user-1",
      githubUsername: "testuser",
      avatarUrl: "https://github.com/avatar.png",
      hasApiKey: false,
    }),
    authGetApiKey: vi.fn().mockRejectedValue(new Error("No key")),
  },
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

  it("shows red dot when user has no API key", () => {
    useAuthStore.setState({ user: mockUser, isLoading: false });
    const { container } = render(
      <PageShell currentStep={0}>
        <div>content</div>
      </PageShell>
    );
    const keyButton = screen.getByLabelText("API key settings");
    expect(keyButton).toBeInTheDocument();
    const dot = container.querySelector(".bg-red-500");
    expect(dot).toBeInTheDocument();
  });

  it("shows green dot when user has API key", () => {
    useAuthStore.setState({
      user: { ...mockUser, hasApiKey: true },
      isLoading: false,
    });
    const { container } = render(
      <PageShell currentStep={0}>
        <div>content</div>
      </PageShell>
    );
    const dot = container.querySelector(".bg-emerald-500");
    expect(dot).toBeInTheDocument();
  });

  it("opens API key setup dialog when key icon is clicked", async () => {
    const user = userEvent.setup();
    useAuthStore.setState({ user: mockUser, isLoading: false });
    render(
      <PageShell currentStep={0}>
        <div>content</div>
      </PageShell>
    );

    await user.click(screen.getByLabelText("API key settings"));
    expect(screen.getByText("Set Up Your API Key")).toBeInTheDocument();
  });

  it("auto-opens API key dialog when autoPromptApiKey is true and user has no key", () => {
    useAuthStore.setState({ user: mockUser, isLoading: false });
    render(
      <PageShell autoPromptApiKey>
        <div>content</div>
      </PageShell>
    );
    expect(screen.getByText("Set Up Your API Key")).toBeInTheDocument();
  });

  it("does not auto-open API key dialog when user already has key", () => {
    useAuthStore.setState({
      user: { ...mockUser, hasApiKey: true },
      isLoading: false,
    });
    render(
      <PageShell autoPromptApiKey>
        <div>content</div>
      </PageShell>
    );
    expect(screen.queryByText("Set Up Your API Key")).not.toBeInTheDocument();
  });

  it("does not auto-open API key dialog when autoPromptApiKey is false", () => {
    useAuthStore.setState({ user: mockUser, isLoading: false });
    render(
      <PageShell>
        <div>content</div>
      </PageShell>
    );
    expect(screen.queryByText("Set Up Your API Key")).not.toBeInTheDocument();
  });
});
