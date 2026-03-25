import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const mockPush = vi.fn();
let mockSearchParams = new URLSearchParams("redirect=/assess");
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => mockSearchParams,
}));

vi.mock("@/lib/auth-store", () => ({
  useAuthStore: () => ({ setUser: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    authLogin: vi.fn(),
    authRegister: vi.fn(),
    authMe: vi.fn().mockResolvedValue({
      userId: "u1",
      displayName: "test",
      avatarUrl: "",
      hasApiKey: false,
      email: "test@example.com",
    }),
  },
}));

import { api } from "@/lib/api";
import LoginPage from "./page";

beforeEach(() => {
  vi.clearAllMocks();
  mockSearchParams = new URLSearchParams("redirect=/assess");
});

describe("LoginPage", () => {
  it("renders sign-in form by default", () => {
    render(<LoginPage />);
    expect(screen.getByPlaceholderText("Email")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
  });

  it("renders register tab", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.click(screen.getByRole("tab", { name: "Register" }));
    expect(screen.getByPlaceholderText("Confirm password")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Create Account" })
    ).toBeInTheDocument();
  });

  it("renders GitHub button", () => {
    render(<LoginPage />);
    expect(screen.getByRole("button", { name: /GitHub/i })).toBeInTheDocument();
  });

  it("shows validation error for mismatched passwords", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.click(screen.getByRole("tab", { name: "Register" }));
    await user.type(screen.getByPlaceholderText("Email"), "test@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "password123");
    await user.type(screen.getByPlaceholderText("Confirm password"), "different");
    await user.click(screen.getByRole("button", { name: "Create Account" }));
    expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
  });

  it("shows validation error for short password", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.click(screen.getByRole("tab", { name: "Register" }));
    await user.type(screen.getByPlaceholderText("Email"), "test@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "short");
    await user.type(screen.getByPlaceholderText("Confirm password"), "short");
    await user.click(screen.getByRole("button", { name: "Create Account" }));
    expect(
      screen.getByText("Password must be at least 8 characters")
    ).toBeInTheDocument();
  });

  it("calls authLogin on sign-in submit", async () => {
    const user = userEvent.setup();
    vi.mocked(api.authLogin).mockResolvedValue(undefined);
    render(<LoginPage />);
    await user.type(screen.getByPlaceholderText("Email"), "test@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(api.authLogin).toHaveBeenCalledWith(
        "test@example.com",
        "password123"
      );
    });
  });

  it("calls authRegister on register submit", async () => {
    const user = userEvent.setup();
    vi.mocked(api.authRegister).mockResolvedValue(undefined);
    render(<LoginPage />);
    await user.click(screen.getByRole("tab", { name: "Register" }));
    await user.type(screen.getByPlaceholderText("Email"), "new@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "password123");
    await user.type(screen.getByPlaceholderText("Confirm password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(api.authRegister).toHaveBeenCalledWith(
        "new@example.com",
        "password123"
      );
    });
  });

  it("redirects after successful login", async () => {
    const user = userEvent.setup();
    vi.mocked(api.authLogin).mockResolvedValue(undefined);
    render(<LoginPage />);
    await user.type(screen.getByPlaceholderText("Email"), "test@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/assess");
    });
  });

  it("shows error on login failure", async () => {
    const user = userEvent.setup();
    vi.mocked(api.authLogin).mockRejectedValue(
      new Error("Invalid email or password")
    );
    render(<LoginPage />);
    await user.type(screen.getByPlaceholderText("Email"), "test@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(
        screen.getByText("Invalid email or password")
      ).toBeInTheDocument();
    });
  });

  it("shows readable message from validation error, not [object Object]", async () => {
    const user = userEvent.setup();
    const err = new Error("Invalid email format; Too short");
    err.name = "ApiError";
    vi.mocked(api.authLogin).mockRejectedValue(err);
    render(<LoginPage />);
    await user.type(screen.getByPlaceholderText("Email"), "test@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "short");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(
        screen.getByText("Invalid email format; Too short")
      ).toBeInTheDocument();
      expect(screen.queryByText("[object Object]")).not.toBeInTheDocument();
    });
  });

  it.each([
    ["https://evil.com", "/dashboard"],
    ["//evil.com", "/dashboard"],
    ["javascript:alert(1)", "/dashboard"],
    ["/dashboard", "/dashboard"],
    [null, "/dashboard"],
  ])(
    "sanitizes redirect param %s to %s",
    async (malicious, expected) => {
      mockSearchParams = new URLSearchParams(
        malicious ? `redirect=${malicious}` : ""
      );
      const user = userEvent.setup();
      vi.mocked(api.authLogin).mockResolvedValue(undefined);
      render(<LoginPage />);
      await user.type(screen.getByPlaceholderText("Email"), "a@b.com");
      await user.type(screen.getByPlaceholderText("Password"), "password123");
      await user.click(screen.getByRole("button", { name: "Sign In" }));

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith(expected);
      });
    }
  );
});
