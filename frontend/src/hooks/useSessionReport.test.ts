import { renderHook, act, waitFor } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("@/lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/api")>();
  return {
    ApiError: mod.ApiError,
    api: {
      assessmentReport: vi.fn(),
    },
  };
});

import { useSessionReport } from "./useSessionReport";
import { api } from "@/lib/api";

const mockedApi = vi.mocked(api);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useSessionReport", () => {
  const mockReport = {
    knowledgeGraph: {
      nodes: [
        {
          concept: "react",
          confidence: 0.8,
          bloomLevel: "apply",
          prerequisites: [],
        },
      ],
    },
    gapAnalysis: {
      overallReadiness: 75,
      summary: "Good progress",
      gaps: [],
    },
    learningPlan: {
      summary: "Focus on advanced topics",
      totalHours: 10,
      phases: [],
    },
    proficiencyScores: [
      {
        skillId: "react",
        skillName: "React",
        score: 80,
        confidence: 0.8,
        reasoning: "Solid understanding",
      },
    ],
  };

  describe("null sessionId", () => {
    it("does not fetch and report stays null", async () => {
      const { result } = renderHook(() => useSessionReport(null));

      // Give a tick for any potential async effects
      await waitFor(() => {
        expect(result.current.report).toBeNull();
      });

      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(mockedApi.assessmentReport).not.toHaveBeenCalled();
    });
  });

  describe("valid sessionId", () => {
    it("fetches and sets report data", async () => {
      mockedApi.assessmentReport.mockResolvedValueOnce(mockReport);

      const { result } = renderHook(() => useSessionReport("sess-1"));

      await waitFor(() => {
        expect(result.current.report).not.toBeNull();
      });

      expect(result.current.report).toEqual(mockReport);
      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(mockedApi.assessmentReport).toHaveBeenCalledWith("sess-1");
    });
  });

  describe("fetch error", () => {
    it("sets error state on failure", async () => {
      mockedApi.assessmentReport.mockRejectedValueOnce(
        new Error("Network failure")
      );

      const { result } = renderHook(() => useSessionReport("sess-1"));

      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
      });

      expect(result.current.error?.message).toBe("Network failure");
      expect(result.current.report).toBeNull();
      expect(result.current.loading).toBe(false);
    });

    it("wraps non-Error throws in a generic Error", async () => {
      mockedApi.assessmentReport.mockRejectedValueOnce("string error");

      const { result } = renderHook(() => useSessionReport("sess-1"));

      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
      });

      expect(result.current.error?.message).toBe("Failed to load report");
      expect(result.current.loading).toBe(false);
    });
  });

  describe("loading state transitions", () => {
    it("transitions from false to true to false on success", async () => {
      let resolvePromise: (value: unknown) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      mockedApi.assessmentReport.mockReturnValueOnce(
        pendingPromise as ReturnType<typeof mockedApi.assessmentReport>
      );

      const { result } = renderHook(() => useSessionReport("sess-1"));

      // Should be loading while fetch is pending
      await waitFor(() => {
        expect(result.current.loading).toBe(true);
      });

      // Resolve the fetch
      await act(async () => {
        resolvePromise!(mockReport);
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.report).toEqual(mockReport);
    });

    it("transitions loading to false on error", async () => {
      mockedApi.assessmentReport.mockRejectedValueOnce(new Error("fail"));

      const { result } = renderHook(() => useSessionReport("sess-1"));

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
        expect(result.current.error).not.toBeNull();
      });
    });
  });

  describe("refetch", () => {
    it("refetches data when refetch is called", async () => {
      mockedApi.assessmentReport.mockResolvedValueOnce(mockReport);

      const { result } = renderHook(() => useSessionReport("sess-1"));

      await waitFor(() => {
        expect(result.current.report).not.toBeNull();
      });

      const updatedReport = {
        ...mockReport,
        gapAnalysis: { ...mockReport.gapAnalysis, overallReadiness: 90 },
      };
      mockedApi.assessmentReport.mockResolvedValueOnce(updatedReport);

      await act(async () => {
        result.current.refetch();
      });

      await waitFor(() => {
        expect(result.current.report?.gapAnalysis.overallReadiness).toBe(90);
      });

      expect(mockedApi.assessmentReport).toHaveBeenCalledTimes(2);
    });
  });
});
