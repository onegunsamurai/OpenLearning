import type { MaterialOut } from "@/lib/types";

/** Matches the JSONB sections array shape from the content pipeline. */
export interface ContentSection {
  type: string;
  title: string;
  body: string;
  code_block: string | null;
  answer: string | null;
}

/** Parsed and validated material ready for rendering. */
export interface ParsedMaterial {
  conceptId: string;
  qualityScore: number;
  qualityFlag: string | null;
  bloomScore: number;
  sections: ContentSection[];
}

/** Known section types for dispatch. */
export type SectionType = "explanation" | "code_example" | "analogy" | "quiz";

/**
 * Parse an opaque MaterialOut.material dict into a typed ParsedMaterial.
 * Returns null if the material structure is invalid.
 */
export function parseMaterial(raw: MaterialOut): ParsedMaterial | null {
  const mat = raw.material as Record<string, unknown>;
  const rawSections = mat?.sections;

  if (!Array.isArray(rawSections)) {
    return null;
  }

  const sections: ContentSection[] = rawSections
    .filter((s): s is Record<string, unknown> => {
      if (typeof s !== "object" || s === null) return false;
      return typeof s.type === "string" && typeof s.title === "string";
    })
    .map((s) => ({
      type: s.type as string,
      title: s.title as string,
      body: typeof s.body === "string" ? s.body : "",
      code_block: typeof s.code_block === "string" ? s.code_block : null,
      answer: typeof s.answer === "string" ? s.answer : null,
    }));

  return {
    conceptId: raw.conceptId,
    qualityScore: raw.qualityScore,
    qualityFlag: raw.qualityFlag ?? null,
    bloomScore: raw.bloomScore,
    sections,
  };
}
