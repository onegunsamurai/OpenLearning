import { renderHook } from "@testing-library/react";
import { useAuth } from "./useAuth";
import { useAuthStore } from "@/lib/auth-store";
import type { AuthMeResponse } from "@/lib/types";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    authLogout: vi.fn(),
  },
}));

import { api } from "@/lib/api";

const mockUser: AuthMeResponse = {
  userId: "user-1",
  displayName: "testuser",
  avatarUrl: "https://github.com/avatar.png",
  hasApiKey: false,
  email: null,
};

describe("useAuth", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isLoading: true });
    vi.clearAllMocks();
  });

  it("does not call authMe on mount", () => {
    renderHook(() => useAuth());

    expect(api.authLogout).not.toHaveBeenCalled();
  });

  it("login navigates to /login page with redirect param", () => {
    const { result } = renderHook(() => useAuth());
    result.current.login("/assess");

    expect(mockPush).toHaveBeenCalledWith(
      `/login?redirect=${encodeURIComponent("/assess")}`
    );
  });

  it("loginWithGithub redirects to GitHub OAuth URL", () => {
    const originalLocation = window.location;
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...originalLocation, href: "", pathname: "/current" },
    });

    const { result } = renderHook(() => useAuth());
    result.current.loginWithGithub("/assess");

    expect(window.location.href).toContain("/api/auth/github?redirect=");
    expect(window.location.href).toContain(encodeURIComponent("/assess"));

    Object.defineProperty(window, "location", {
      writable: true,
      value: originalLocation,
    });
  });

  it("logout calls api and clears store", async () => {
    vi.mocked(api.authLogout).mockResolvedValue(undefined);

    useAuthStore.getState().setUser(mockUser);

    const { result } = renderHook(() => useAuth());
    await result.current.logout();

    expect(api.authLogout).toHaveBeenCalled();
    expect(useAuthStore.getState().user).toBeNull();
  });
});
