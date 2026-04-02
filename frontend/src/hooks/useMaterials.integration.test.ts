/**
 * Integration tests: useMaterials hook → parseMaterial pipeline
 *
 * These tests exercise the real boundary between the hook and parseMaterial.
 * Only api.getMaterials is mocked (the external API boundary). parseMaterial
 * runs for real so the Map built by the hook reflects genuine parse behaviour.
 */

import { vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  api: {
    getMaterials: vi.fn(),
  },
}));

// Speed up polling to keep the test suite fast.
vi.mock("@/lib/constants", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return { ...actual, MATERIALS_POLL_INTERVAL_MS: 50, MATERIALS_MAX_RETRIES: 2 };
});

import { api } from "@/lib/api";
import { useMaterials } from "./useMaterials";
import type { MaterialsResponse, MaterialOut } from "@/lib/types";

const mockGetMaterials = vi.mocked(api.getMaterials);

// ── Helpers ─────────────────────────────────────────────────────────────

function makeResponse(materials: MaterialOut[]): MaterialsResponse {
  return { sessionId: "sess-integration", materials };
}

function makeValidMaterial(conceptId: string, overrides?: Partial<MaterialOut>): MaterialOut {
  return {
    conceptId,
    domain: "backend_engineering",
    bloomScore: 0.8,
    qualityScore: 0.9,
    iterationCount: 1,
    qualityFlag: null,
    material: {
      sections: [
        { type: "explanation", title: "What it is", body: "An explanation." },
        { type: "code_example", title: "In practice", body: "See code:", code_block: "const x = 1;" },
        { type: "analogy", title: "Think of it like", body: "A library book." },
        { type: "quiz", title: "Test yourself", body: "What is x?", answer: "1" },
      ],
    },
    generatedAt: "2026-04-01T00:00:00Z",
    ...overrides,
  };
}

function makeInvalidMaterial(conceptId: string): MaterialOut {
  return {
    conceptId,
    domain: "backend_engineering",
    bloomScore: 0.5,
    qualityScore: 0.5,
    iterationCount: 1,
    qualityFlag: null,
    // No sections array — parseMaterial returns null for this shape.
    material: { not_sections: "wrong" },
    generatedAt: "2026-04-01T00:00:00Z",
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

// ── Tests ────────────────────────────────────────────────────────────────

describe("useMaterials → parseMaterial integration", () => {
  it("builds Map keyed by conceptId for every parseable material in the API response", async () => {
    mockGetMaterials.mockResolvedValue(
      makeResponse([
        makeValidMaterial("concept-alpha"),
        makeValidMaterial("concept-beta"),
        makeValidMaterial("concept-gamma"),
      ])
    );

    const { result } = renderHook(() => useMaterials("sess-integration"));

    await waitFor(() => expect(result.current.materialsByConceptId.size).toBe(3));

    expect(result.current.materialsByConceptId.has("concept-alpha")).toBe(true);
    expect(result.current.materialsByConceptId.has("concept-beta")).toBe(true);
    expect(result.current.materialsByConceptId.has("concept-gamma")).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("parsed ParsedMaterial carries all four section types with correct fields", async () => {
    mockGetMaterials.mockResolvedValue(
      makeResponse([makeValidMaterial("concept-alpha")])
    );

    const { result } = renderHook(() => useMaterials("sess-integration"));

    await waitFor(() => expect(result.current.materialsByConceptId.size).toBe(1));

    const parsed = result.current.materialsByConceptId.get("concept-alpha")!;
    expect(parsed.sections).toHaveLength(4);

    const [explanation, code, analogy, quiz] = parsed.sections;
    expect(explanation.type).toBe("explanation");
    expect(explanation.body).toBe("An explanation.");

    expect(code.type).toBe("code_example");
    expect(code.code_block).toBe("const x = 1;");

    expect(analogy.type).toBe("analogy");

    expect(quiz.type).toBe("quiz");
    expect(quiz.answer).toBe("1");
  });

  it("excludes materials that parseMaterial rejects while keeping valid ones", async () => {
    mockGetMaterials.mockResolvedValue(
      makeResponse([
        makeValidMaterial("good-concept"),
        makeInvalidMaterial("bad-concept"),
        makeValidMaterial("another-good"),
        // Sections is not an array.
        {
          ...makeInvalidMaterial("also-bad"),
          material: { sections: "not-an-array" },
        },
      ])
    );

    const { result } = renderHook(() => useMaterials("sess-integration"));

    await waitFor(() => expect(result.current.loading).toBe(false));

    // Only two valid materials should be in the Map.
    expect(result.current.materialsByConceptId.size).toBe(2);
    expect(result.current.materialsByConceptId.has("good-concept")).toBe(true);
    expect(result.current.materialsByConceptId.has("another-good")).toBe(true);
    expect(result.current.materialsByConceptId.has("bad-concept")).toBe(false);
    expect(result.current.materialsByConceptId.has("also-bad")).toBe(false);
  });

  it("propagates qualityFlag through to the ParsedMaterial in the Map", async () => {
    mockGetMaterials.mockResolvedValue(
      makeResponse([
        makeValidMaterial("flagged-concept", {
          qualityFlag: "max_iterations_reached",
          qualityScore: 0.55,
        }),
      ])
    );

    const { result } = renderHook(() => useMaterials("sess-integration"));

    await waitFor(() => expect(result.current.materialsByConceptId.size).toBe(1));

    const parsed = result.current.materialsByConceptId.get("flagged-concept")!;
    expect(parsed.qualityFlag).toBe("max_iterations_reached");
    expect(parsed.qualityScore).toBe(0.55);
  });

  it("empty sections array parses successfully and produces an entry with zero sections", async () => {
    mockGetMaterials.mockResolvedValue(
      makeResponse([
        makeValidMaterial("empty-sections", {
          material: { sections: [] },
        }),
      ])
    );

    const { result } = renderHook(() => useMaterials("sess-integration"));

    await waitFor(() => expect(result.current.loading).toBe(false));

    // parseMaterial returns a valid ParsedMaterial with empty sections array
    // so the hook keeps it in the Map (map.size > 0 triggers stop-polling).
    expect(result.current.materialsByConceptId.size).toBe(1);
    const parsed = result.current.materialsByConceptId.get("empty-sections")!;
    expect(parsed.sections).toHaveLength(0);
  });

  it("mixed sections where some lack type/title are filtered by parseMaterial before entering Map", async () => {
    mockGetMaterials.mockResolvedValue(
      makeResponse([
        makeValidMaterial("mixed-concept", {
          material: {
            sections: [
              // Valid
              { type: "explanation", title: "Good", body: "ok" },
              // Missing type — parseMaterial filters this out.
              { title: "No type", body: "skip" },
              // Missing title — parseMaterial filters this out.
              { type: "quiz", body: "skip" },
            ],
          },
        }),
      ])
    );

    const { result } = renderHook(() => useMaterials("sess-integration"));

    await waitFor(() => expect(result.current.materialsByConceptId.size).toBe(1));

    const parsed = result.current.materialsByConceptId.get("mixed-concept")!;
    // Only the valid section survives parseMaterial's filter.
    expect(parsed.sections).toHaveLength(1);
    expect(parsed.sections[0].title).toBe("Good");
  });

  it("empty API response starts polling and sets pollingExhausted after max retries", async () => {
    // Always empty so polling exhausts.
    mockGetMaterials.mockResolvedValue(makeResponse([]));

    const { result } = renderHook(() => useMaterials("sess-integration"));

    // With MAX_RETRIES=2 and POLL_INTERVAL=50ms this should exhaust quickly.
    await waitFor(
      () => expect(result.current.pollingExhausted).toBe(true),
      { timeout: 3000 }
    );

    expect(result.current.materialsByConceptId.size).toBe(0);
    // Initial fetch + 2 poll retries = 3 total calls.
    expect(mockGetMaterials).toHaveBeenCalledTimes(3);
  });
});
