/**
 * Integration tests: MaterialsPanel → ContentSectionRenderer → section components
 *
 * These tests exercise the full render tree: a ParsedMaterial flowing through
 * MaterialsPanel into ContentSectionRenderer which dispatches to each concrete
 * section component.  No sub-components are mocked — the real dispatch and real
 * rendering are exercised together.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ParsedMaterial, ContentSection } from "@/lib/materials";
import { MaterialsPanel } from "./materials-panel";

// ── Helpers ──────────────────────────────────────────────────────────────

function makeSection(overrides: Partial<ContentSection>): ContentSection {
  return {
    type: "explanation",
    title: "Default",
    body: "Default body",
    code_block: null,
    answer: null,
    ...overrides,
  };
}

function makeMaterial(overrides: Partial<ParsedMaterial> = {}): ParsedMaterial {
  return {
    conceptId: "http_fundamentals",
    qualityScore: 0.9,
    qualityFlag: null,
    bloomScore: 0.85,
    sections: [],
    ...overrides,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────

describe("MaterialsPanel → ContentSectionRenderer → section components (integration)", () => {
  it("expanding the panel renders all four section types through the real dispatch chain", async () => {
    const user = userEvent.setup();
    const material = makeMaterial({
      sections: [
        makeSection({ type: "explanation", title: "Explain HTTP", body: "HTTP is a protocol." }),
        makeSection({
          type: "code_example",
          title: "HTTP in code",
          body: "Here is a fetch:",
          code_block: "fetch('/api/data')",
        }),
        makeSection({ type: "analogy", title: "Like a waiter", body: "A request is an order." }),
        makeSection({
          type: "quiz",
          title: "What does GET do?",
          body: "Choose the best description.",
          answer: "Retrieves a resource without side effects.",
        }),
      ],
    });

    render(<MaterialsPanel material={material} />);

    // Panel starts collapsed — no section titles visible.
    expect(screen.queryByText("Explain HTTP")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Toggle learning materials" }));

    // ExplanationSection renders title and body.
    expect(screen.getByText("Explain HTTP")).toBeInTheDocument();
    expect(screen.getByText("HTTP is a protocol.")).toBeInTheDocument();

    // CodeExampleSection renders the code block in a <pre><code> element.
    expect(screen.getByText("HTTP in code")).toBeInTheDocument();
    const codeEl = screen.getByText("fetch('/api/data')");
    expect(codeEl.tagName).toBe("CODE");

    // AnalogySection renders with its left-border accent wrapper.
    const analogyTitle = screen.getByText("Like a waiter");
    expect(analogyTitle).toBeInTheDocument();
    const analogyWrapper = analogyTitle.closest(".border-l-2");
    expect(analogyWrapper).not.toBeNull();

    // QuizSection renders body and a "Show Answer" toggle; answer is hidden.
    expect(screen.getByText("What does GET do?")).toBeInTheDocument();
    expect(screen.getByText("Choose the best description.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /show answer/i })).toBeInTheDocument();
    expect(
      screen.queryByText("Retrieves a resource without side effects.")
    ).not.toBeInTheDocument();
  });

  it("quiz answer reveal works when panel is expanded", async () => {
    const user = userEvent.setup();
    const material = makeMaterial({
      sections: [
        makeSection({
          type: "quiz",
          title: "Quiz question",
          body: "What is REST?",
          answer: "Representational State Transfer",
        }),
      ],
    });

    render(<MaterialsPanel material={material} />);

    await user.click(screen.getByRole("button", { name: "Toggle learning materials" }));

    // Answer hidden initially.
    expect(screen.queryByText("Representational State Transfer")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /show answer/i }));

    expect(screen.getByText("Representational State Transfer")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /hide answer/i })).toBeInTheDocument();
  });

  it("unknown section type falls back to ExplanationSection without throwing", async () => {
    const user = userEvent.setup();
    const material = makeMaterial({
      sections: [
        makeSection({
          type: "future_type_not_yet_implemented",
          title: "Future content",
          body: "This will render via the fallback path.",
        }),
      ],
    });

    render(<MaterialsPanel material={material} />);
    await user.click(screen.getByRole("button", { name: "Toggle learning materials" }));

    expect(screen.getByText("Future content")).toBeInTheDocument();
    expect(screen.getByText("This will render via the fallback path.")).toBeInTheDocument();
  });

  it("quality badge reflects qualityFlag flowing from ParsedMaterial through to the rendered badge", async () => {
    const material = makeMaterial({
      qualityScore: 0.5,
      qualityFlag: "max_iterations_reached",
    });

    render(<MaterialsPanel material={material} />);

    // QualityBadge reads qualityFlag and renders "Review Suggested" text.
    expect(screen.getByText("Review Suggested")).toBeInTheDocument();
  });

  it("quality badge shows 'High Quality' for high score with no flag", async () => {
    const material = makeMaterial({ qualityScore: 0.9, qualityFlag: null });

    render(<MaterialsPanel material={material} />);

    expect(screen.getByText("High Quality")).toBeInTheDocument();
  });

  it("quality badge shows 'Acceptable' for mid-range score with no flag", async () => {
    const material = makeMaterial({ qualityScore: 0.7, qualityFlag: null });

    render(<MaterialsPanel material={material} />);

    expect(screen.getByText("Acceptable")).toBeInTheDocument();
  });

  it("quality badge shows 'Needs Review' for low score with no flag", async () => {
    const material = makeMaterial({ qualityScore: 0.4, qualityFlag: null });

    render(<MaterialsPanel material={material} />);

    expect(screen.getByText("Needs Review")).toBeInTheDocument();
  });

  it("code_example section without a code_block renders body only and no <pre>", async () => {
    const user = userEvent.setup();
    const material = makeMaterial({
      sections: [
        makeSection({
          type: "code_example",
          title: "No code here",
          body: "Just prose.",
          code_block: null,
        }),
      ],
    });

    const { container } = render(<MaterialsPanel material={material} />);
    await user.click(screen.getByRole("button", { name: "Toggle learning materials" }));

    expect(screen.getByText("Just prose.")).toBeInTheDocument();
    expect(container.querySelector("pre")).toBeNull();
  });

  it("each section is keyed uniquely so multiple sections of the same type render without conflicts", async () => {
    const user = userEvent.setup();
    const material = makeMaterial({
      sections: [
        makeSection({ type: "explanation", title: "First", body: "Body one" }),
        makeSection({ type: "explanation", title: "Second", body: "Body two" }),
        makeSection({ type: "explanation", title: "Third", body: "Body three" }),
      ],
    });

    render(<MaterialsPanel material={material} />);
    await user.click(screen.getByRole("button", { name: "Toggle learning materials" }));

    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
    expect(screen.getByText("Third")).toBeInTheDocument();
    expect(screen.getByText("Body one")).toBeInTheDocument();
    expect(screen.getByText("Body two")).toBeInTheDocument();
    expect(screen.getByText("Body three")).toBeInTheDocument();
  });

  it("'No content available' message renders when sections array is empty", async () => {
    const user = userEvent.setup();
    const material = makeMaterial({ sections: [] });

    render(<MaterialsPanel material={material} />);
    await user.click(screen.getByRole("button", { name: "Toggle learning materials" }));

    expect(screen.getByText("No content available")).toBeInTheDocument();
  });

  it("collapsing the panel hides all section content again", async () => {
    const user = userEvent.setup();
    const material = makeMaterial({
      sections: [
        makeSection({ type: "explanation", title: "Visible When Open", body: "Content here" }),
      ],
    });

    render(<MaterialsPanel material={material} />);

    const toggleBtn = screen.getByRole("button", { name: "Toggle learning materials" });

    // Open.
    await user.click(toggleBtn);
    expect(screen.getByText("Visible When Open")).toBeInTheDocument();

    // Close.
    await user.click(toggleBtn);
    expect(screen.queryByText("Visible When Open")).not.toBeInTheDocument();
  });

  it("analogy section contains the Lightbulb icon sibling next to the title", async () => {
    const user = userEvent.setup();
    const material = makeMaterial({
      sections: [
        makeSection({ type: "analogy", title: "Like a recipe", body: "Step by step." }),
      ],
    });

    render(<MaterialsPanel material={material} />);
    await user.click(screen.getByRole("button", { name: "Toggle learning materials" }));

    // The Lightbulb icon and title sit inside a flex row.
    const titleEl = screen.getByText("Like a recipe");
    const iconRow = titleEl.parentElement!;
    expect(iconRow.className).toContain("flex");
    // The Lightbulb icon is an SVG element inside the same flex container.
    expect(iconRow.querySelector("svg")).not.toBeNull();
  });
});
