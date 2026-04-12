import { render, screen, within } from "@testing-library/react";
import { PlanTimeline } from "./PlanTimeline";
import type { AssessmentReportResponse } from "@/lib/types";

type Plan = AssessmentReportResponse["learningPlan"];

/**
 * Regression tests for issue #168 — per-concept resources.
 *
 * Before the fix, every concept card in a phase rendered the SAME phase-level
 * resources list. After the fix, each concept card renders ONLY its own
 * resources (i.e. `concept.resources`).
 */

const plan: Plan = {
  summary: "A focused plan",
  totalHours: 10,
  phases: [
    {
      phaseNumber: 1,
      title: "Async Fundamentals",
      rationale: "Get comfortable with the event loop.",
      estimatedHours: 10,
      concepts: [
        {
          key: "event-loop",
          name: "Event Loop",
          description: "How the loop schedules coroutines.",
          resources: [
            {
              type: "article",
              title: "Event Loop Primer",
              url: "https://example.com/el",
            },
          ],
        },
        {
          key: "futures",
          name: "Futures",
          description: "Awaiting coroutines and futures.",
          resources: [
            {
              type: "video",
              title: "Futures Explained",
              url: "https://example.com/f",
            },
          ],
        },
        {
          key: "cancellation",
          name: "Cancellation",
          description: "Propagating task cancellation correctly.",
          resources: [
            { type: "project", title: "Cancellation Lab", url: null },
          ],
        },
      ],
    },
  ],
};

describe("PlanTimeline", () => {
  it("renders the active phase title and rationale", () => {
    render(<PlanTimeline plan={plan} activePhase={1} />);
    expect(
      screen.getByRole("heading", { name: /Async Fundamentals/ })
    ).toBeInTheDocument();
    expect(
      screen.getByText("Get comfortable with the event loop.")
    ).toBeInTheDocument();
  });

  it("renders one concept card per concept with its own name and description", () => {
    render(<PlanTimeline plan={plan} activePhase={1} />);
    expect(screen.getByRole("heading", { name: "Event Loop" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Futures" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cancellation" })).toBeInTheDocument();

    expect(
      screen.getByText("How the loop schedules coroutines.")
    ).toBeInTheDocument();
    expect(screen.getByText("Awaiting coroutines and futures.")).toBeInTheDocument();
  });

  it("each concept shows only its own resources (regression for #168)", () => {
    const { container } = render(<PlanTimeline plan={plan} activePhase={1} />);

    // Each concept card is a rounded border container — find them via the
    // concept heading and walk up to its card.
    const getCardByHeading = (name: string) => {
      const heading = screen.getByRole("heading", { name });
      const card = heading.closest("div.rounded-xl");
      if (!card) throw new Error(`Card for ${name} not found`);
      return card as HTMLElement;
    };

    const eventLoopCard = getCardByHeading("Event Loop");
    expect(within(eventLoopCard).getByText("Event Loop Primer")).toBeInTheDocument();
    expect(within(eventLoopCard).queryByText("Futures Explained")).not.toBeInTheDocument();
    expect(within(eventLoopCard).queryByText("Cancellation Lab")).not.toBeInTheDocument();

    const futuresCard = getCardByHeading("Futures");
    expect(within(futuresCard).getByText("Futures Explained")).toBeInTheDocument();
    expect(within(futuresCard).queryByText("Event Loop Primer")).not.toBeInTheDocument();
    expect(within(futuresCard).queryByText("Cancellation Lab")).not.toBeInTheDocument();

    const cancellationCard = getCardByHeading("Cancellation");
    expect(within(cancellationCard).getByText("Cancellation Lab")).toBeInTheDocument();
    expect(within(cancellationCard).queryByText("Event Loop Primer")).not.toBeInTheDocument();
    expect(within(cancellationCard).queryByText("Futures Explained")).not.toBeInTheDocument();

    // There should be exactly three concept cards in this phase.
    expect(container.querySelectorAll("div.rounded-xl")).toHaveLength(3);
  });

  it("renders an external link for resources with a URL", () => {
    render(<PlanTimeline plan={plan} activePhase={1} />);
    const link = screen.getByRole("link", { name: /Event Loop Primer/ });
    expect(link).toHaveAttribute("href", "https://example.com/el");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("renders plain text for resources without a URL", () => {
    render(<PlanTimeline plan={plan} activePhase={1} />);
    // Cancellation Lab has url=null — it must render but not as a link.
    expect(screen.getByText("Cancellation Lab")).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /Cancellation Lab/ })
    ).not.toBeInTheDocument();
  });

  it("returns null when activePhase has no matching phase", () => {
    const { container } = render(<PlanTimeline plan={plan} activePhase={99} />);
    expect(container).toBeEmptyDOMElement();
  });
});
