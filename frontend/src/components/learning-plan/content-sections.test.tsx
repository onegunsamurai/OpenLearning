import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ContentSection } from "@/lib/materials";
import {
  ExplanationSection,
  CodeExampleSection,
  AnalogySection,
  QuizSection,
} from "./content-sections";

const baseSection: ContentSection = {
  type: "explanation",
  title: "Test Title",
  body: "Test body content",
  code_block: null,
  answer: null,
};

describe("ExplanationSection", () => {
  it("renders title as heading and body text", () => {
    render(<ExplanationSection section={baseSection} />);
    expect(screen.getByText("Test Title")).toBeInTheDocument();
    expect(screen.getByText("Test body content")).toBeInTheDocument();
  });

  it("does not render code block element", () => {
    const { container } = render(
      <ExplanationSection section={baseSection} />
    );
    expect(container.querySelector("pre")).toBeNull();
  });
});

describe("CodeExampleSection", () => {
  it("renders title, body, and code block", () => {
    const section: ContentSection = {
      ...baseSection,
      type: "code_example",
      code_block: "const x = 1;",
    };
    render(<CodeExampleSection section={section} />);
    expect(screen.getByText("Test Title")).toBeInTheDocument();
    expect(screen.getByText("Test body content")).toBeInTheDocument();
    expect(screen.getByText("const x = 1;")).toBeInTheDocument();
  });

  it("handles null code_block", () => {
    const section: ContentSection = {
      ...baseSection,
      type: "code_example",
      code_block: null,
    };
    const { container } = render(
      <CodeExampleSection section={section} />
    );
    expect(screen.getByText("Test Title")).toBeInTheDocument();
    expect(container.querySelector("pre")).toBeNull();
  });

  it("code block has overflow-x-auto for long lines", () => {
    const section: ContentSection = {
      ...baseSection,
      type: "code_example",
      code_block: "x".repeat(300),
    };
    const { container } = render(
      <CodeExampleSection section={section} />
    );
    const pre = container.querySelector("pre");
    expect(pre).not.toBeNull();
    expect(pre!.className).toContain("overflow-x-auto");
  });
});

describe("AnalogySection", () => {
  it("renders title and body with visual accent", () => {
    const section: ContentSection = {
      ...baseSection,
      type: "analogy",
    };
    render(<AnalogySection section={section} />);
    expect(screen.getByText("Test Title")).toBeInTheDocument();
    expect(screen.getByText("Test body content")).toBeInTheDocument();
  });

  it("has a left border accent class", () => {
    const section: ContentSection = { ...baseSection, type: "analogy" };
    const { container } = render(
      <AnalogySection section={section} />
    );
    const wrapper = container.firstElementChild;
    expect(wrapper!.className).toContain("border-l-2");
  });
});

describe("QuizSection", () => {
  const quizSection: ContentSection = {
    ...baseSection,
    type: "quiz",
    body: "What is 2+2?",
    answer: "The answer is 4",
  };

  it("renders title and body (question)", () => {
    render(<QuizSection section={quizSection} />);
    expect(screen.getByText("Test Title")).toBeInTheDocument();
    expect(screen.getByText("What is 2+2?")).toBeInTheDocument();
  });

  it("answer is hidden by default", () => {
    render(<QuizSection section={quizSection} />);
    expect(screen.queryByText("The answer is 4")).not.toBeInTheDocument();
    expect(screen.getByText("Show Answer")).toBeInTheDocument();
  });

  it("click 'Show Answer' reveals the answer", async () => {
    const user = userEvent.setup();
    render(<QuizSection section={quizSection} />);

    await user.click(screen.getByText("Show Answer"));
    expect(screen.getByText("The answer is 4")).toBeInTheDocument();
    expect(screen.getByText("Hide Answer")).toBeInTheDocument();
  });

  it("toggle button has aria-controls linking to answer region", () => {
    render(<QuizSection section={quizSection} />);
    const button = screen.getByRole("button", { name: /show answer/i });
    expect(button).toHaveAttribute("aria-controls");
    const controlsId = button.getAttribute("aria-controls")!;
    expect(document.getElementById(controlsId)).toBeInTheDocument();
  });

  it("handles null answer (no toggle shown)", () => {
    const section: ContentSection = {
      ...quizSection,
      answer: null,
    };
    render(<QuizSection section={section} />);
    expect(screen.queryByText("Show Answer")).not.toBeInTheDocument();
  });
});
