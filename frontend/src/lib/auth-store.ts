import { create } from "zustand";
import type { AuthMeResponse } from "@/lib/types";

interface AuthState {
  user: AuthMeResponse | null;
  isLoading: boolean;
  setUser: (user: AuthMeResponse | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  isLoading: true,
  setUser: (user) => set({ user, isLoading: false }),
  setLoading: (isLoading) => set({ isLoading }),
  logout: () => set({ user: null, isLoading: false }),
}));
