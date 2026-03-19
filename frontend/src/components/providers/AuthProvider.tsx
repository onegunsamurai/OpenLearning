"use client";

import { useAuth } from "@/hooks/useAuth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Trigger the auth check on mount; state lives in useAuthStore
  useAuth();
  return <>{children}</>;
}
