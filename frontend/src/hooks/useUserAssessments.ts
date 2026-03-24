"use client";

import { useState, useEffect, useCallback, useRef } from "react";
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
  const requestIdRef = useRef(0);

  const fetchSessions = useCallback(async () => {
    const currentRequestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getUserAssessments();
      if (requestIdRef.current === currentRequestId) {
        setSessions(data);
      }
    } catch (err) {
      if (requestIdRef.current === currentRequestId) {
        setError(
          err instanceof Error ? err : new Error("Failed to load assessments")
        );
      }
    } finally {
      if (requestIdRef.current === currentRequestId) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return { sessions, loading, error, refetch: fetchSessions };
}
