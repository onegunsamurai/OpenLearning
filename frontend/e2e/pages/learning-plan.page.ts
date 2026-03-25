import { type Locator, type Page, expect } from "@playwright/test";

export class LearningPlanPage {
  readonly page: Page;
  readonly loadingText: Locator;
  readonly phasesLabel: Locator;
  readonly phaseButtons: Locator;
  readonly copyButton: Locator;
  readonly exportLink: Locator;
  readonly startOverButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.loadingText = page.getByText("Loading your learning plan...");
    this.phasesLabel = page.getByText("Phases");
    this.phaseButtons = page.getByRole("button", { name: /phase \d+/i });
    this.copyButton = page.getByRole("button", { name: /save plan/i });
    this.exportLink = page.getByRole("link", { name: /export report/i });
    this.startOverButton = page.getByRole("button", { name: /start over/i });
  }

  async goto(sessionId?: string) {
    const url = sessionId
      ? `/learning-plan?session=${sessionId}`
      : "/learning-plan";
    await this.page.goto(url);
  }

  async expectLoaded() {
    await expect(this.phasesLabel).toBeVisible();
  }

  async expectLoading() {
    await expect(this.loadingText).toBeVisible();
  }

  async getPhaseCount() {
    return this.phaseButtons.count();
  }

  async selectPhase(phaseNumber: number) {
    await this.phaseButtons
      .filter({ hasText: `Phase ${phaseNumber}` })
      .click();
  }

  async startOver() {
    await this.startOverButton.click();
  }
}
