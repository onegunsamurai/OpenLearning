import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import type { UserAssessmentSummary } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/dashboard",
  useSearchParams: () => new URLSearchParams(),
}));

// next/link renders as a plain <a> in jsdom
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

import { AssessmentCard } from "./AssessmentCard";

function makeSession(
  overrides: Partial<UserAssessmentSummary> = {}
): UserAssessmentSummary {
  return {
    sessionId: "sess-100",
    status: "active",
    skillIds: ["react", "typescript"],
    targetLevel: "mid",
    createdAt: "2025-06-15T10:00:00Z",
    completedAt: null,
    overallReadiness: null,
    skillCount: 2,
    ...overrides,
  };
}

describe("AssessmentCard", () => {
  describe("completed session", () => {
    it("renders readiness score and View Results link", () => {
      const session = makeSession({
        status: "completed",
        overallReadiness: 78,
        completedAt: "2025-06-16T12:00:00Z",
      });

      render(<AssessmentCard session={session} index={0} />);

      expect(screen.getByText("78%")).toBeInTheDocument();
      expect(screen.getByText("Readiness")).toBeInTheDocument();
      expect(screen.getByText("Completed")).toBeInTheDocument();

      const viewLink = screen.getByRole("link", { name: /view results/i });
      expect(viewLink).toHaveAttribute(
        "href",
        "/gap-analysis?session=sess-100"
      );
    });
  });

  describe("active session", () => {
    it("renders Resume link to assess page", () => {
      const session = makeSession({ status: "active" });

      render(<AssessmentCard session={session} index={0} />);

      expect(screen.getByText("In Progress")).toBeInTheDocument();

      const resumeLink = screen.getByRole("link", { name: /resume/i });
      expect(resumeLink).toHaveAttribute("href", "/assess?session=sess-100");
    });

    it("does not render readiness score", () => {
      const session = makeSession({ status: "active" });

      render(<AssessmentCard session={session} index={0} />);

      expect(screen.queryByText("Readiness")).not.toBeInTheDocument();
    });
  });

  describe("timed_out session", () => {
    it("renders Start New link", () => {
      const session = makeSession({ status: "timed_out" });

      render(<AssessmentCard session={session} index={0} />);

      expect(screen.getByText("Timed Out")).toBeInTheDocument();

      const startLink = screen.getByRole("link", { name: /start new/i });
      expect(startLink).toHaveAttribute("href", "/");
    });
  });

  describe("error session", () => {
    it("renders Error badge and Start New link", () => {
      const session = makeSession({ status: "error" });

      render(<AssessmentCard session={session} index={0} />);

      expect(screen.getByText("Error")).toBeInTheDocument();

      const startLink = screen.getByRole("link", { name: /start new/i });
      expect(startLink).toHaveAttribute("href", "/");
    });

    it("does not render readiness score", () => {
      const session = makeSession({ status: "error", overallReadiness: 0 });

      render(<AssessmentCard session={session} index={0} />);

      expect(screen.queryByText("Readiness")).not.toBeInTheDocument();
    });

    it("does not render View Results link", () => {
      const session = makeSession({ status: "error" });

      render(<AssessmentCard session={session} index={0} />);

      expect(screen.queryByRole("link", { name: /view results/i })).not.toBeInTheDocument();
    });

    it("does not render completedAt even when present", () => {
      const session = makeSession({ status: "error", completedAt: "2025-06-16T12:00:00Z" });

      render(<AssessmentCard session={session} index={0} />);

      expect(screen.queryByText(/completed/i)).not.toBeInTheDocument();
    });
  });

  describe("date formatting", () => {
    it("formats createdAt date correctly", () => {
      const session = makeSession({ createdAt: "2025-06-15T10:00:00Z" });

      render(<AssessmentCard session={session} index={0} />);

      // toLocaleDateString with month: "short", day: "numeric", year: "numeric"
      expect(screen.getByText(/Jun 15, 2025/)).toBeInTheDocument();
    });

    it("renders skill count", () => {
      const session = makeSession({ skillCount: 3 });

      render(<AssessmentCard session={session} index={0} />);

      expect(screen.getByText(/3 skills/)).toBeInTheDocument();
    });

    it("renders singular skill for count of 1", () => {
      const session = makeSession({ skillCount: 1 });

      render(<AssessmentCard session={session} index={0} />);

      expect(screen.getByText(/1 skill(?!s)/)).toBeInTheDocument();
    });
  });
});
