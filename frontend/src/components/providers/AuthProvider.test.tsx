import { render, waitFor } from "@testing-library/react";
import { AuthProvider } from "./AuthProvider";
import { useAuthStore } from "@/lib/auth-store";
import type { AuthMeResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  api: {
    authMe: vi.fn(),
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

describe("AuthProvider", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isLoading: true });
    vi.clearAllMocks();
  });

  it("calls authMe on mount and sets user on success", async () => {
    vi.mocked(api.authMe).mockResolvedValue(mockUser);

    render(
      <AuthProvider>
        <div>child</div>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(api.authMe).toHaveBeenCalledTimes(1);
      expect(useAuthStore.getState().user).toEqual(mockUser);
      expect(useAuthStore.getState().isLoading).toBe(false);
    });
  });

  it("sets user to null on authMe failure", async () => {
    vi.mocked(api.authMe).mockRejectedValue(new Error("401"));

    render(
      <AuthProvider>
        <div>child</div>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(useAuthStore.getState().user).toBeNull();
      expect(useAuthStore.getState().isLoading).toBe(false);
    });
  });

  it("only calls authMe once", async () => {
    vi.mocked(api.authMe).mockResolvedValue(mockUser);

    const { rerender } = render(
      <AuthProvider>
        <div>child</div>
      </AuthProvider>
    );

    rerender(
      <AuthProvider>
        <div>child updated</div>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(api.authMe).toHaveBeenCalledTimes(1);
    });
  });
});
