import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ApiKeySetup } from "./api-key-setup";

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    authGetApiKey: vi.fn().mockResolvedValue(null),
    authValidateKey: vi.fn(),
    authSetApiKey: vi.fn(),
    authDeleteApiKey: vi.fn(),
  },
}));

import { api } from "@/lib/api";

const mockApi = api as unknown as {
  authGetApiKey: ReturnType<typeof vi.fn>;
  authValidateKey: ReturnType<typeof vi.fn>;
  authSetApiKey: ReturnType<typeof vi.fn>;
  authDeleteApiKey: ReturnType<typeof vi.fn>;
};

describe("ApiKeySetup", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.authGetApiKey.mockResolvedValue(null);
  });

  it("renders dialog when open", () => {
    render(<ApiKeySetup open={true} onClose={vi.fn()} />);

    expect(screen.getByText("Set Up Your API Key")).toBeInTheDocument();
    expect(screen.getByText(/console\.anthropic\.com/)).toBeInTheDocument();
    expect(screen.getByLabelText("API key")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Validate & Save/ })).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    render(<ApiKeySetup open={false} onClose={vi.fn()} />);

    expect(screen.queryByText("Set Up Your API Key")).not.toBeInTheDocument();
  });

  it("accepts text in the input field", async () => {
    const user = userEvent.setup();
    render(<ApiKeySetup open={true} onClose={vi.fn()} />);

    const input = screen.getByLabelText("API key");
    await user.type(input, "sk-ant-test123");
    expect(input).toHaveValue("sk-ant-test123");
  });

  it("toggles show/hide for the key input", async () => {
    const user = userEvent.setup();
    render(<ApiKeySetup open={true} onClose={vi.fn()} />);

    const input = screen.getByLabelText("API key");
    expect(input).toHaveAttribute("type", "password");

    await user.click(screen.getByLabelText("Show API key"));
    expect(input).toHaveAttribute("type", "text");

    await user.click(screen.getByLabelText("Hide API key"));
    expect(input).toHaveAttribute("type", "password");
  });

  it("shows error on invalid key", async () => {
    const user = userEvent.setup();
    mockApi.authValidateKey.mockResolvedValue({ valid: false, error: "Invalid API key" });
    render(<ApiKeySetup open={true} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText("API key"), "sk-bad");
    await user.click(screen.getByRole("button", { name: /Validate & Save/ }));

    expect(await screen.findByText("Invalid API key")).toBeInTheDocument();
  });

  it("calls onKeySet and onClose on success", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const onClose = vi.fn();
    const onKeySet = vi.fn();

    mockApi.authValidateKey.mockResolvedValue({ valid: true });
    mockApi.authSetApiKey.mockResolvedValue(undefined);

    render(<ApiKeySetup open={true} onClose={onClose} onKeySet={onKeySet} />);

    await user.type(screen.getByLabelText("API key"), "sk-valid");
    await user.click(screen.getByRole("button", { name: /Validate & Save/ }));

    // Wait for success state and setTimeout
    expect(await screen.findByText("Saved!")).toBeInTheDocument();

    vi.advanceTimersByTime(1000);
    expect(onKeySet).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();

    vi.useRealTimers();
  });

  it("shows save-specific error when validation passes but save fails", async () => {
    const user = userEvent.setup();
    mockApi.authValidateKey.mockResolvedValue({ valid: true });
    mockApi.authSetApiKey.mockRejectedValue(new Error("Network error"));

    render(<ApiKeySetup open={true} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText("API key"), "sk-valid");
    await user.click(screen.getByRole("button", { name: /Validate & Save/ }));

    expect(
      await screen.findByText("Key is valid but failed to save. Please try again.")
    ).toBeInTheDocument();
  });

  it("renders a close button and skip button", () => {
    render(<ApiKeySetup open={true} onClose={vi.fn()} />);

    expect(screen.getByLabelText("Close")).toBeInTheDocument();
    expect(screen.getByText("Skip for now")).toBeInTheDocument();
  });

  it("calls onClose when X close button is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<ApiKeySetup open={true} onClose={onClose} />);

    await user.click(screen.getByLabelText("Close"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose when Skip for now is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<ApiKeySetup open={true} onClose={onClose} />);

    await user.click(screen.getByText("Skip for now"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("shows existing key preview when available", async () => {
    mockApi.authGetApiKey.mockResolvedValue({ apiKeyPreview: "sk-...1234" });

    render(<ApiKeySetup open={true} onClose={vi.fn()} />);

    expect(await screen.findByText("sk-...1234")).toBeInTheDocument();
    expect(screen.getByText("Current key")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Update Key/ })).toBeInTheDocument();
  });
});
