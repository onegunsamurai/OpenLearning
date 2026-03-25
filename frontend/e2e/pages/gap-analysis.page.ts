import { type Locator, type Page, expect } from "@playwright/test";

export class GapAnalysisPage {
  readonly page: Page;
  readonly loadingText: Locator;
  readonly heading: Locator;
  readonly gapCards: Locator;
  readonly readinessHeading: Locator;
  readonly generatePlanButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.loadingText = page.getByText("Loading gap analysis...");
    this.heading = page.getByRole("heading", { name: /skill gap breakdown/i });
    // Gap cards each contain an h4 skill name heading
    this.gapCards = page.getByRole("heading", { level: 4 }).locator("..");
    this.readinessHeading = page.getByRole("heading", {
      name: /overall readiness/i,
    });
    this.generatePlanButton = page.getByRole("button", {
      name: /generate learning plan/i,
    });
  }

  async goto(sessionId?: string) {
    const url = sessionId
      ? `/gap-analysis?session=${sessionId}`
      : "/gap-analysis";
    await this.page.goto(url);
  }

  async expectLoaded() {
    await expect(this.heading).toBeVisible();
  }

  async expectLoading() {
    await expect(this.loadingText).toBeVisible();
  }

  async getGapCardCount() {
    return this.gapCards.count();
  }

  async generateLearningPlan() {
    await this.generatePlanButton.click();
  }
}
