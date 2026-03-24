import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...props
  }: {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders 'No assessments yet' text", () => {
    render(<EmptyState />);
    expect(screen.getByText("No assessments yet")).toBeInTheDocument();
  });

  it("renders 'Start Assessment' link pointing to home", () => {
    render(<EmptyState />);
    const link = screen.getByRole("link", { name: /start assessment/i });
    expect(link).toHaveAttribute("href", "/");
  });

  it("renders descriptive paragraph text", () => {
    render(<EmptyState />);
    expect(
      screen.getByText(/start your first skill assessment/i)
    ).toBeInTheDocument();
  });
});
