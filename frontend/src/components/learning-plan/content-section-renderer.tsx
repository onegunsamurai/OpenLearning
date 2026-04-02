"use client";

import type { ComponentType } from "react";
import type { ContentSection, SectionType } from "@/lib/materials";
import {
  ExplanationSection,
  CodeExampleSection,
  AnalogySection,
  QuizSection,
} from "./content-sections";

interface ContentSectionRendererProps {
  section: ContentSection;
}

const SECTION_COMPONENTS: Record<
  SectionType,
  ComponentType<{ section: ContentSection }>
> = {
  explanation: ExplanationSection,
  code_example: CodeExampleSection,
  analogy: AnalogySection,
  quiz: QuizSection,
};

export function ContentSectionRenderer({
  section,
}: ContentSectionRendererProps) {
  const Component =
    SECTION_COMPONENTS[section.type as SectionType] ?? ExplanationSection;
  return <Component section={section} />;
}
