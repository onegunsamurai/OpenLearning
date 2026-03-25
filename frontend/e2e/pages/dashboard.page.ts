import { type Locator, type Page, expect } from "@playwright/test";

export class DashboardPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly newAssessmentButton: Locator;
  readonly assessmentCards: Locator;
  readonly profileCard: Locator;
  readonly emptyState: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole("heading", { name: "Your Assessments" });
    this.newAssessmentButton = page.getByRole("link", {
      name: "New Assessment",
    });
    this.assessmentCards = page.locator("[class*=grid] > div");
    this.profileCard = page.locator("div").filter({ hasText: /Profile|e2e/i }).first();
    this.emptyState = page.getByText("No assessments yet");
  }

  async goto() {
    await this.page.goto("/dashboard");
  }

  async expectLoaded() {
    await expect(this.heading).toBeVisible();
  }

  async startNewAssessment() {
    await this.newAssessmentButton.click();
  }
}
