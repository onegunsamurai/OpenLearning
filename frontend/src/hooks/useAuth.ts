"use client";

import { useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { api } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useAuth() {
  const { user, isLoading, setUser, logout: clearStore } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    api
      .authMe()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      });
    return () => {
      cancelled = true;
    };
  }, [setUser]);

  const login = useCallback(
    (redirectPath?: string) => {
      const redirect = redirectPath ?? window.location.pathname;
      router.push(`/login?redirect=${encodeURIComponent(redirect)}`);
    },
    [router]
  );

  const loginWithGithub = useCallback((redirectPath?: string) => {
    const redirect = redirectPath ?? window.location.pathname;
    window.location.href = `${API_URL}/api/auth/github?redirect=${encodeURIComponent(redirect)}`;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.authLogout();
    } finally {
      clearStore();
    }
  }, [clearStore]);

  return { user, isLoading, login, loginWithGithub, logout };
}
