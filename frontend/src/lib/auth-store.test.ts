import { useAuthStore } from "./auth-store";
import type { AuthMeResponse } from "./types";

const mockUser: AuthMeResponse = {
  userId: "user-1",
  githubUsername: "testuser",
  avatarUrl: "https://github.com/avatar.png",
  hasApiKey: false,
};

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isLoading: true });
  });

  it("starts with null user and loading true", () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isLoading).toBe(true);
  });

  it("setUser sets user and stops loading", () => {
    useAuthStore.getState().setUser(mockUser);
    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.isLoading).toBe(false);
  });

  it("setUser(null) clears user and stops loading", () => {
    useAuthStore.getState().setUser(mockUser);
    useAuthStore.getState().setUser(null);
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isLoading).toBe(false);
  });

  it("logout clears user and stops loading", () => {
    useAuthStore.getState().setUser(mockUser);
    useAuthStore.getState().logout();
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isLoading).toBe(false);
  });

  it("setLoading updates isLoading", () => {
    useAuthStore.getState().setLoading(false);
    expect(useAuthStore.getState().isLoading).toBe(false);
    useAuthStore.getState().setLoading(true);
    expect(useAuthStore.getState().isLoading).toBe(true);
  });
});
