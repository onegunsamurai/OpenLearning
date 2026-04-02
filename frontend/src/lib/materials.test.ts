import type { MaterialOut } from "@/lib/types";
import { parseMaterial } from "./materials";

function makeMaterialOut(
  material: Record<string, unknown>,
  overrides?: Partial<MaterialOut>
): MaterialOut {
  return {
    conceptId: "concept-1",
    domain: "test-domain",
    bloomScore: 0.85,
    qualityScore: 0.9,
    iterationCount: 1,
    qualityFlag: null,
    material,
    generatedAt: "2026-04-01T00:00:00Z",
    ...overrides,
  };
}

describe("parseMaterial", () => {
  it("returns ParsedMaterial for valid data", () => {
    const raw = makeMaterialOut({
      concept_id: "concept-1",
      sections: [
        {
          type: "explanation",
          title: "Test Title",
          body: "Test body",
          code_block: null,
          answer: null,
        },
      ],
    });

    const result = parseMaterial(raw);
    expect(result).not.toBeNull();
    expect(result!.conceptId).toBe("concept-1");
    expect(result!.qualityScore).toBe(0.9);
    expect(result!.bloomScore).toBe(0.85);
    expect(result!.qualityFlag).toBeNull();
    expect(result!.sections).toHaveLength(1);
    expect(result!.sections[0]).toEqual({
      type: "explanation",
      title: "Test Title",
      body: "Test body",
      code_block: null,
      answer: null,
    });
  });

  it("returns null when sections is missing", () => {
    const raw = makeMaterialOut({ concept_id: "c1" });
    expect(parseMaterial(raw)).toBeNull();
  });

  it("returns null when sections is not an array", () => {
    const raw = makeMaterialOut({ sections: "not-an-array" });
    expect(parseMaterial(raw)).toBeNull();
  });

  it("defaults missing code_block and answer to null", () => {
    const raw = makeMaterialOut({
      sections: [{ type: "explanation", title: "T", body: "B" }],
    });

    const result = parseMaterial(raw)!;
    expect(result.sections[0].code_block).toBeNull();
    expect(result.sections[0].answer).toBeNull();
  });

  it("defaults missing body to empty string", () => {
    const raw = makeMaterialOut({
      sections: [{ type: "explanation", title: "T" }],
    });

    const result = parseMaterial(raw)!;
    expect(result.sections[0].body).toBe("");
  });

  it("skips sections missing type or title", () => {
    const raw = makeMaterialOut({
      sections: [
        { type: "explanation", title: "Valid", body: "ok" },
        { title: "No type", body: "skip" },
        { type: "quiz", body: "skip" },
        { type: "analogy", title: "Also valid", body: "ok" },
      ],
    });

    const result = parseMaterial(raw)!;
    expect(result.sections).toHaveLength(2);
    expect(result.sections[0].title).toBe("Valid");
    expect(result.sections[1].title).toBe("Also valid");
  });

  it("skips non-object sections", () => {
    const raw = makeMaterialOut({
      sections: [
        "not-an-object",
        null,
        42,
        { type: "explanation", title: "Good", body: "ok" },
      ],
    });

    const result = parseMaterial(raw)!;
    expect(result.sections).toHaveLength(1);
  });

  it("handles empty sections array", () => {
    const raw = makeMaterialOut({ sections: [] });

    const result = parseMaterial(raw)!;
    expect(result).not.toBeNull();
    expect(result.sections).toHaveLength(0);
  });

  it("preserves qualityFlag when present", () => {
    const raw = makeMaterialOut(
      { sections: [] },
      { qualityFlag: "max_iterations_reached" }
    );

    const result = parseMaterial(raw)!;
    expect(result.qualityFlag).toBe("max_iterations_reached");
  });

  it("handles all four section types", () => {
    const raw = makeMaterialOut({
      sections: [
        { type: "explanation", title: "E", body: "explanation body" },
        {
          type: "code_example",
          title: "C",
          body: "code body",
          code_block: "const x = 1;",
        },
        { type: "analogy", title: "A", body: "analogy body" },
        {
          type: "quiz",
          title: "Q",
          body: "question?",
          answer: "the answer",
        },
      ],
    });

    const result = parseMaterial(raw)!;
    expect(result.sections).toHaveLength(4);
    expect(result.sections[0].type).toBe("explanation");
    expect(result.sections[1].code_block).toBe("const x = 1;");
    expect(result.sections[2].type).toBe("analogy");
    expect(result.sections[3].answer).toBe("the answer");
  });

  it("passes through extra fields without crashing", () => {
    const raw = makeMaterialOut({
      sections: [
        {
          type: "explanation",
          title: "T",
          body: "B",
          extra_field: "ignored",
        },
      ],
      unknown_top_level: true,
    });

    const result = parseMaterial(raw);
    expect(result).not.toBeNull();
    expect(result!.sections[0]).not.toHaveProperty("extra_field");
  });
});
