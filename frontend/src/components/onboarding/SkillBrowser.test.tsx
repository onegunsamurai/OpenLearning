import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SkillBrowser } from "./SkillBrowser";
import type { Skill } from "@/lib/types";

const skills: Skill[] = [
  {
    id: "s1",
    name: "React",
    category: "Frontend",
    icon: "react",
    description: "UI library",
    subSkills: ["Hooks", "JSX"],
  },
  {
    id: "s2",
    name: "TypeScript",
    category: "Frontend",
    icon: "ts",
    description: "Typed JS",
    subSkills: ["Generics", "Types"],
  },
  {
    id: "s3",
    name: "Python",
    category: "Backend",
    icon: "py",
    description: "General purpose",
    subSkills: ["Django", "FastAPI"],
  },
];

const categories = ["Frontend", "Backend"];

const defaultProps = {
  skills,
  categories,
  selectedSkillIds: [] as string[],
  onToggleSkill: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("SkillBrowser", () => {
  it("renders all categories", () => {
    render(<SkillBrowser {...defaultProps} />);
    expect(screen.getByText("Frontend")).toBeInTheDocument();
    expect(screen.getByText("Backend")).toBeInTheDocument();
  });

  it("renders all skills", () => {
    render(<SkillBrowser {...defaultProps} />);
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
  });

  it("groups skills under correct categories", () => {
    const { container } = render(<SkillBrowser {...defaultProps} />);
    // Frontend section should contain React and TypeScript
    const headings = container.querySelectorAll("h3");
    expect(headings[0].textContent).toBe("Frontend");
    expect(headings[1].textContent).toBe("Backend");
  });

  it("filters by skill name", async () => {
    const user = userEvent.setup();
    render(<SkillBrowser {...defaultProps} />);

    await user.type(screen.getByPlaceholderText("Search skills..."), "React");

    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.queryByText("TypeScript")).not.toBeInTheDocument();
    expect(screen.queryByText("Python")).not.toBeInTheDocument();
  });

  it("filters by category name", async () => {
    const user = userEvent.setup();
    render(<SkillBrowser {...defaultProps} />);

    await user.type(
      screen.getByPlaceholderText("Search skills..."),
      "Backend"
    );

    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.queryByText("React")).not.toBeInTheDocument();
  });

  it("filters by sub-skill name", async () => {
    const user = userEvent.setup();
    render(<SkillBrowser {...defaultProps} />);

    await user.type(
      screen.getByPlaceholderText("Search skills..."),
      "Django"
    );

    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.queryByText("React")).not.toBeInTheDocument();
  });

  it("filters case-insensitively", async () => {
    const user = userEvent.setup();
    render(<SkillBrowser {...defaultProps} />);

    await user.type(
      screen.getByPlaceholderText("Search skills..."),
      "react"
    );

    expect(screen.getByText("React")).toBeInTheDocument();
  });

  it("shows all skills when search is cleared", async () => {
    const user = userEvent.setup();
    render(<SkillBrowser {...defaultProps} />);

    const input = screen.getByPlaceholderText("Search skills...");
    await user.type(input, "React");
    await user.clear(input);

    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
  });

  it("hides empty categories after filtering", async () => {
    const user = userEvent.setup();
    render(<SkillBrowser {...defaultProps} />);

    await user.type(
      screen.getByPlaceholderText("Search skills..."),
      "Python"
    );

    expect(screen.queryByText("Frontend")).not.toBeInTheDocument();
    expect(screen.getByText("Backend")).toBeInTheDocument();
  });

  it("calls onToggleSkill with correct ID on click", async () => {
    const onToggle = vi.fn();
    const user = userEvent.setup();
    render(<SkillBrowser {...defaultProps} onToggleSkill={onToggle} />);

    await user.click(screen.getByText("React"));

    expect(onToggle).toHaveBeenCalledWith("s1");
  });

  it("shows no results when search matches nothing", async () => {
    const user = userEvent.setup();
    render(<SkillBrowser {...defaultProps} />);

    await user.type(
      screen.getByPlaceholderText("Search skills..."),
      "ZZZZZ"
    );

    expect(screen.queryByText("Frontend")).not.toBeInTheDocument();
    expect(screen.queryByText("Backend")).not.toBeInTheDocument();
  });

  it("renders selected state for skills", () => {
    render(<SkillBrowser {...defaultProps} selectedSkillIds={["s1"]} />);
    const reactButton = screen.getByText("React").closest("button");
    expect(reactButton?.className).toContain("border-cyan");
    expect(reactButton?.className).toContain("bg-cyan-muted");
  });

  it("shows Check icon for selected skill", () => {
    const { container } = render(
      <SkillBrowser {...defaultProps} selectedSkillIds={["s1"]} />
    );
    // lucide Check icon renders with class lucide-check
    expect(container.querySelector(".lucide-check")).toBeInTheDocument();
  });

  it("does not show Check icon for unselected skills", () => {
    const { container } = render(
      <SkillBrowser {...defaultProps} selectedSkillIds={[]} />
    );
    expect(container.querySelector(".lucide-check")).not.toBeInTheDocument();
  });

  it("renders unselected skill with default styling", () => {
    render(<SkillBrowser {...defaultProps} selectedSkillIds={[]} />);
    const reactButton = screen.getByText("React").closest("button");
    expect(reactButton?.className).toContain("border-border");
    expect(reactButton?.className).toContain("bg-secondary");
  });

  it("handles multiple skills selected simultaneously", () => {
    const { container } = render(
      <SkillBrowser {...defaultProps} selectedSkillIds={["s1", "s3"]} />
    );
    const reactButton = screen.getByText("React").closest("button");
    const pythonButton = screen.getByText("Python").closest("button");
    const tsButton = screen.getByText("TypeScript").closest("button");

    expect(reactButton?.className).toContain("border-cyan");
    expect(pythonButton?.className).toContain("border-cyan");
    expect(tsButton?.className).toContain("border-border");

    // Two Check icons should appear (for s1 and s3)
    const checks = container.querySelectorAll(".lucide-check");
    expect(checks).toHaveLength(2);
  });
});
