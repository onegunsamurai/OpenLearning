import { render, screen } from "@testing-library/react";
import { ContentSectionRenderer } from "./content-section-renderer";
import type { ContentSection } from "@/lib/materials";

function makeSection(overrides: Partial<ContentSection> = {}): ContentSection {
  return {
    type: "explanation",
    title: "Default Title",
    body: "Default body",
    code_block: null,
    answer: null,
    ...overrides,
  };
}

describe("ContentSectionRenderer", () => {
  it("dispatches explanation type to ExplanationSection", () => {
    render(
      <ContentSectionRenderer
        section={makeSection({ type: "explanation", title: "Explain This" })}
      />
    );
    expect(screen.getByText("Explain This")).toBeInTheDocument();
  });

  it("dispatches code_example type to CodeExampleSection", () => {
    render(
      <ContentSectionRenderer
        section={makeSection({
          type: "code_example",
          title: "Code",
          code_block: "let x = 1;",
        })}
      />
    );
    expect(screen.getByText("let x = 1;")).toBeInTheDocument();
  });

  it("dispatches analogy type to AnalogySection", () => {
    const { container } = render(
      <ContentSectionRenderer
        section={makeSection({ type: "analogy", title: "Like a Library" })}
      />
    );
    expect(screen.getByText("Like a Library")).toBeInTheDocument();
    expect(container.querySelector(".border-l-2")).not.toBeNull();
  });

  it("dispatches quiz type to QuizSection", () => {
    render(
      <ContentSectionRenderer
        section={makeSection({
          type: "quiz",
          title: "Quiz Time",
          answer: "42",
        })}
      />
    );
    expect(screen.getByText("Quiz Time")).toBeInTheDocument();
    expect(screen.getByText("Show Answer")).toBeInTheDocument();
  });

  it("falls back to ExplanationSection for unknown type", () => {
    render(
      <ContentSectionRenderer
        section={makeSection({
          type: "future_type",
          title: "Future Content",
          body: "Unknown but rendered",
        })}
      />
    );
    expect(screen.getByText("Future Content")).toBeInTheDocument();
    expect(screen.getByText("Unknown but rendered")).toBeInTheDocument();
  });
});
