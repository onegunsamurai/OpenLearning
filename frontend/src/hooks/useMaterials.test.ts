import { vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  api: {
    getMaterials: vi.fn(),
  },
}));

vi.mock("@/lib/constants", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    MATERIALS_POLL_INTERVAL_MS: 50,
    MATERIALS_MAX_RETRIES: 2,
  };
});

import { api } from "@/lib/api";
import { useMaterials } from "./useMaterials";
import type { MaterialsResponse } from "@/lib/types";

const mockGetMaterials = vi.mocked(api.getMaterials);

function makeMaterialsResponse(
  materials: MaterialsResponse["materials"] = []
): MaterialsResponse {
  return { sessionId: "sess-1", materials };
}

function makeRawMaterial(conceptId: string) {
  return {
    conceptId,
    domain: "test",
    bloomScore: 0.8,
    qualityScore: 0.9,
    iterationCount: 1,
    qualityFlag: null,
    material: {
      sections: [
        { type: "explanation", title: "T", body: "B" },
      ],
    },
    generatedAt: "2026-01-01T00:00:00Z",
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useMaterials", () => {
  it("returns materialsByConceptId Map on success", async () => {
    mockGetMaterials.mockResolvedValue(
      makeMaterialsResponse([makeRawMaterial("concept-a")])
    );

    const { result } = renderHook(() => useMaterials("sess-1"));

    await waitFor(() =>
      expect(result.current.materialsByConceptId.size).toBe(1)
    );
    expect(result.current.materialsByConceptId.has("concept-a")).toBe(true);
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it("returns error on API failure", async () => {
    mockGetMaterials.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useMaterials("sess-1"));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error!.message).toBe("Network error");
    expect(result.current.materialsByConceptId.size).toBe(0);
  });

  it("returns empty Map when API returns empty materials", async () => {
    mockGetMaterials.mockResolvedValue(makeMaterialsResponse([]));

    const { result } = renderHook(() => useMaterials("sess-1"));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.materialsByConceptId.size).toBe(0);
  });

  it("does not fetch when sessionId is null", () => {
    renderHook(() => useMaterials(null));
    expect(mockGetMaterials).not.toHaveBeenCalled();
  });

  it("skips materials with invalid structure", async () => {
    mockGetMaterials.mockResolvedValue(
      makeMaterialsResponse([
        makeRawMaterial("good"),
        {
          conceptId: "bad",
          domain: "test",
          bloomScore: 0.5,
          qualityScore: 0.5,
          iterationCount: 1,
          qualityFlag: null,
          material: { no_sections: true } as Record<string, unknown>,
          generatedAt: "2026-01-01T00:00:00Z",
        },
      ])
    );

    const { result } = renderHook(() => useMaterials("sess-1"));

    await waitFor(() =>
      expect(result.current.materialsByConceptId.size).toBe(1)
    );
    expect(result.current.materialsByConceptId.has("good")).toBe(true);
    expect(result.current.materialsByConceptId.has("bad")).toBe(false);
  });

  it("polls when materials are empty and stops when they arrive", async () => {
    mockGetMaterials
      .mockResolvedValueOnce(makeMaterialsResponse([]))
      .mockResolvedValueOnce(makeMaterialsResponse([makeRawMaterial("c1")]));

    const { result } = renderHook(() => useMaterials("sess-1"));

    // Wait for materials to arrive after polling
    await waitFor(
      () => expect(result.current.materialsByConceptId.size).toBe(1),
      { timeout: 3000 }
    );
  });

  it("stops polling after max retries and sets pollingExhausted", async () => {
    mockGetMaterials.mockResolvedValue(makeMaterialsResponse([]));

    const { result } = renderHook(() => useMaterials("sess-1"));

    // With MAX_RETRIES=2 and POLL_INTERVAL=50ms, should exhaust within 500ms
    await waitFor(
      () => expect(result.current.pollingExhausted).toBe(true),
      { timeout: 3000 }
    );

    // Initial + 2 retries = 3 calls
    expect(mockGetMaterials).toHaveBeenCalledTimes(3);
  });

  it("retry resets counter and re-fetches", async () => {
    mockGetMaterials.mockResolvedValue(makeMaterialsResponse([]));

    const { result } = renderHook(() => useMaterials("sess-1"));

    // Wait for polling exhaustion
    await waitFor(
      () => expect(result.current.pollingExhausted).toBe(true),
      { timeout: 3000 }
    );

    const callCountAfterExhaustion = mockGetMaterials.mock.calls.length;

    // Set up materials for retry
    mockGetMaterials.mockResolvedValue(
      makeMaterialsResponse([makeRawMaterial("c1")])
    );

    act(() => result.current.retry());

    await waitFor(() =>
      expect(result.current.materialsByConceptId.size).toBe(1)
    );
    expect(result.current.pollingExhausted).toBe(false);
    expect(mockGetMaterials.mock.calls.length).toBeGreaterThan(
      callCountAfterExhaustion
    );
  });

  it("handles non-Error thrown values", async () => {
    mockGetMaterials.mockRejectedValue("string error");

    const { result } = renderHook(() => useMaterials("sess-1"));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error!.message).toBe("Failed to load materials");
  });
});
