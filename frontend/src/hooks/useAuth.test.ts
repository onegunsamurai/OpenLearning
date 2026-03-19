import { renderHook, waitFor } from "@testing-library/react";
import { useAuth } from "./useAuth";
import { useAuthStore } from "@/lib/auth-store";
import type { AuthMeResponse } from "@/lib/types";

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    authMe: vi.fn(),
    authLogout: vi.fn(),
  },
}));

import { api } from "@/lib/api";

const mockUser: AuthMeResponse = {
  userId: "user-1",
  githubUsername: "testuser",
  avatarUrl: "https://github.com/avatar.png",
  hasApiKey: false,
};

describe("useAuth", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isLoading: true });
    vi.clearAllMocks();
  });

  it("calls authMe on mount and sets user on success", async () => {
    vi.mocked(api.authMe).mockResolvedValue(mockUser);

    renderHook(() => useAuth());

    await waitFor(() => {
      expect(useAuthStore.getState().user).toEqual(mockUser);
      expect(useAuthStore.getState().isLoading).toBe(false);
    });
  });

  it("sets user to null on authMe failure", async () => {
    vi.mocked(api.authMe).mockRejectedValue(new Error("401"));

    renderHook(() => useAuth());

    await waitFor(() => {
      expect(useAuthStore.getState().user).toBeNull();
      expect(useAuthStore.getState().isLoading).toBe(false);
    });
  });

  it("login redirects to GitHub OAuth URL", () => {
    vi.mocked(api.authMe).mockResolvedValue(mockUser);

    // Mock window.location
    const originalLocation = window.location;
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...originalLocation, href: "", pathname: "/current" },
    });

    const { result } = renderHook(() => useAuth());
    result.current.login("/assess");

    expect(window.location.href).toContain("/api/auth/github?redirect=");
    expect(window.location.href).toContain(encodeURIComponent("/assess"));

    // Restore
    Object.defineProperty(window, "location", {
      writable: true,
      value: originalLocation,
    });
  });

  it("logout calls api and clears store", async () => {
    vi.mocked(api.authMe).mockResolvedValue(mockUser);
    vi.mocked(api.authLogout).mockResolvedValue(undefined);

    // Set user first
    useAuthStore.getState().setUser(mockUser);

    const { result } = renderHook(() => useAuth());
    await result.current.logout();

    expect(api.authLogout).toHaveBeenCalled();
    expect(useAuthStore.getState().user).toBeNull();
  });
});
