"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import { parseMaterial, type ParsedMaterial } from "@/lib/materials";
import {
  MATERIALS_POLL_INTERVAL_MS,
  MATERIALS_MAX_RETRIES,
} from "@/lib/constants";

export interface UseMaterialsResult {
  materialsByConceptId: Map<string, ParsedMaterial>;
  loading: boolean;
  error: Error | null;
  retry: () => void;
  pollingExhausted: boolean;
}

export function useMaterials(
  sessionId: string | null
): UseMaterialsResult {
  const [materialsByConceptId, setMaterialsByConceptId] = useState<
    Map<string, ParsedMaterial>
  >(new Map());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [pollingExhausted, setPollingExhausted] = useState(false);
  const [retrySignal, setRetrySignal] = useState(0);
  const requestIdRef = useRef(0);
  const pollCountRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const hasMaterialsRef = useRef(false);

  const fetchMaterials = useCallback(async () => {
    if (!sessionId) return;

    const currentRequestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);

    try {
      const data = await api.getMaterials(sessionId);

      if (requestIdRef.current !== currentRequestId) return;

      const map = new Map<string, ParsedMaterial>();
      for (const raw of data.materials) {
        const parsed = parseMaterial(raw);
        if (parsed) {
          map.set(parsed.conceptId, parsed);
        }
      }

      setMaterialsByConceptId(map);
      setLoading(false);
      hasMaterialsRef.current = map.size > 0;
    } catch (err) {
      if (requestIdRef.current !== currentRequestId) return;
      setError(
        err instanceof Error ? err : new Error("Failed to load materials")
      );
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;

    // Cancel any previous interval synchronously before starting a new cycle
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    pollCountRef.current = 0;
    hasMaterialsRef.current = false;

    // Fire initial fetch — same pattern as useSessionReport; the lint rule flags it
    // because fetchMaterials calls setState, but this is the standard data-fetching effect pattern.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchMaterials();

    // Start polling; interval self-terminates when materials are found or retries exhausted
    intervalRef.current = setInterval(() => {
      if (hasMaterialsRef.current) {
        clearInterval(intervalRef.current!);
        intervalRef.current = null;
        return;
      }

      pollCountRef.current += 1;

      if (pollCountRef.current > MATERIALS_MAX_RETRIES) {
        clearInterval(intervalRef.current!);
        intervalRef.current = null;
        setPollingExhausted(true);
        return;
      }

      fetchMaterials();
    }, MATERIALS_POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [sessionId, fetchMaterials, retrySignal]);

  const retry = useCallback(() => {
    setPollingExhausted(false);
    setError(null);
    setRetrySignal((s) => s + 1);
  }, []);

  return { materialsByConceptId, loading, error, retry, pollingExhausted };
}
