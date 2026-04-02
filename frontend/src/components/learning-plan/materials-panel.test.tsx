import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ParsedMaterial } from "@/lib/materials";
import { MaterialsPanel } from "./materials-panel";

function makeMaterial(
  overrides: Partial<ParsedMaterial> = {}
): ParsedMaterial {
  return {
    conceptId: "concept-1",
    qualityScore: 0.85,
    qualityFlag: null,
    bloomScore: 0.8,
    sections: [
      {
        type: "explanation",
        title: "Explanation Title",
        body: "Explanation body text",
        code_block: null,
        answer: null,
      },
    ],
    ...overrides,
  };
}

describe("MaterialsPanel", () => {
  it("renders collapsed by default", () => {
    render(<MaterialsPanel material={makeMaterial()} />);
    expect(screen.getByText("Learning Materials")).toBeInTheDocument();
    expect(screen.queryByText("Explanation Title")).not.toBeInTheDocument();
  });

  it("expands on click and shows sections", async () => {
    const user = userEvent.setup();
    render(<MaterialsPanel material={makeMaterial()} />);

    await user.click(screen.getByText("Learning Materials"));
    expect(screen.getByText("Explanation Title")).toBeInTheDocument();
    expect(screen.getByText("Explanation body text")).toBeInTheDocument();
  });

  it("shows QualityBadge", () => {
    render(<MaterialsPanel material={makeMaterial()} />);
    expect(screen.getByText("High Quality")).toBeInTheDocument();
  });

  it("shows 'No content available' when sections are empty", async () => {
    const user = userEvent.setup();
    render(<MaterialsPanel material={makeMaterial({ sections: [] })} />);

    await user.click(screen.getByText("Learning Materials"));
    expect(screen.getByText("No content available")).toBeInTheDocument();
  });

  it("renders all section types", async () => {
    const user = userEvent.setup();
    const material = makeMaterial({
      sections: [
        {
          type: "explanation",
          title: "Explain",
          body: "E body",
          code_block: null,
          answer: null,
        },
        {
          type: "code_example",
          title: "Code",
          body: "C body",
          code_block: "const x = 1;",
          answer: null,
        },
        {
          type: "analogy",
          title: "Analogy",
          body: "A body",
          code_block: null,
          answer: null,
        },
        {
          type: "quiz",
          title: "Quiz",
          body: "Q body",
          code_block: null,
          answer: "The answer",
        },
      ],
    });

    render(<MaterialsPanel material={material} />);
    await user.click(screen.getByText("Learning Materials"));

    expect(screen.getByText("Explain")).toBeInTheDocument();
    expect(screen.getByText("Code")).toBeInTheDocument();
    expect(screen.getByText("const x = 1;")).toBeInTheDocument();
    expect(screen.getByText("Analogy")).toBeInTheDocument();
    expect(screen.getByText("Quiz")).toBeInTheDocument();
  });

  it("toggle button has correct aria-expanded", async () => {
    const user = userEvent.setup();
    render(<MaterialsPanel material={makeMaterial()} />);

    const button = screen.getByRole("button", {
      name: "Toggle learning materials",
    });
    expect(button).toHaveAttribute("aria-expanded", "false");

    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
  });
});
