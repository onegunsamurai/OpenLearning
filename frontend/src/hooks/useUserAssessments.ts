"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { UserAssessmentSummary } from "@/lib/types";

interface UseUserAssessmentsResult {
  sessions: UserAssessmentSummary[];
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useUserAssessments(): UseUserAssessmentsResult {
  const [sessions, setSessions] = useState<UserAssessmentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getUserAssessments();
      setSessions(data);
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error("Failed to load assessments")
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return { sessions, loading, error, refetch: fetchSessions };
}
