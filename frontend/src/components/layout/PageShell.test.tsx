import { render, screen } from "@testing-library/react";

import { PageShell } from "./PageShell";

describe("PageShell", () => {
  it("renders 'Try Demo' link when isDemo is false", () => {
    render(
      <PageShell currentStep={0}>
        <div>content</div>
      </PageShell>
    );
    const link = screen.getByRole("link", { name: /Try Demo/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/demo/assess");
  });

  it("does not render 'Try Demo' link when isDemo is true", () => {
    render(
      <PageShell currentStep={0} isDemo>
        <div>content</div>
      </PageShell>
    );
    expect(screen.queryByRole("link", { name: /Try Demo/i })).not.toBeInTheDocument();
  });

  it("renders 'Demo' badge when isDemo is true", () => {
    render(
      <PageShell currentStep={0} isDemo>
        <div>content</div>
      </PageShell>
    );
    expect(screen.getByText("Demo")).toBeInTheDocument();
  });
});
