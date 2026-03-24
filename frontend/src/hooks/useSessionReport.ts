"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api, AssessmentReportResponse } from "@/lib/api";

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
  const cancelledRef = useRef(false);

  const fetchReport = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);
    try {
      const data = await api.assessmentReport(sessionId);
      if (!cancelledRef.current) {
        setReport(data);
      }
    } catch (err) {
      if (!cancelledRef.current) {
        setError(
          err instanceof Error ? err : new Error("Failed to load report")
        );
      }
    } finally {
      if (!cancelledRef.current) {
        setLoading(false);
      }
    }
  }, [sessionId]);

  useEffect(() => {
    cancelledRef.current = false;

    if (sessionId) {
      fetchReport();
    }

    return () => {
      cancelledRef.current = true;
    };
  }, [sessionId, fetchReport]);

  return { report, loading, error, refetch: fetchReport };
}
