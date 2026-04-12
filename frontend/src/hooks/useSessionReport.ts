"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { AssessmentReportResponse } from "@/lib/types";

interface UseSessionReportResult {
  report: AssessmentReportResponse | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useSessionReport(
  sessionId: string | null
): UseSessionReportResult {
  const [report, setReport] = useState<AssessmentReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const requestIdRef = useRef(0);

  const fetchReport = useCallback(async () => {
    if (!sessionId) return;

    const currentRequestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);
    try {
      const data = await api.assessmentReport(sessionId);
      if (requestIdRef.current === currentRequestId) {
        setReport(data);
      }
    } catch (err) {
      if (requestIdRef.current === currentRequestId) {
        setError(
          err instanceof Error ? err : new Error("Failed to load report")
        );
      }
    } finally {
      if (requestIdRef.current === currentRequestId) {
        setLoading(false);
      }
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionId) {
      fetchReport();
    }
  }, [sessionId, fetchReport]);

  return { report, loading, error, refetch: fetchReport };
}
