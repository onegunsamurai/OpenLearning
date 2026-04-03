import { type Locator, type Page, expect } from "@playwright/test";

export class AssessmentPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly chatInput: Locator;
  readonly sendButton: Locator;
  readonly chatMessages: Locator;
  readonly typingIndicator: Locator;
  readonly progressBar: Locator;
  readonly progressText: Locator;
  readonly errorDisplay: Locator;
  readonly retryButton: Locator;

  // Completion state
  readonly completionHeading: Locator;
  readonly viewGapAnalysisButton: Locator;
  readonly averageProficiency: Locator;
  readonly scoreCards: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole("heading", { name: /skill assessment/i });
    this.chatInput = page.getByPlaceholder("Type your answer...");
    this.sendButton = page.locator('button[type="submit"]');
    this.chatMessages = page.locator("main .space-y-4 > div");
    this.typingIndicator = page.locator("[class*=typing], [class*=animate-pulse]");
    this.progressBar = page.locator('[role="progressbar"]');
    this.progressText = page.getByText(/question \d+ of/i);
    this.errorDisplay = page.getByRole("alert");
    this.retryButton = page.getByRole("button", { name: /retry/i });

    // Completion
    this.completionHeading = page.getByRole("heading", {
      name: /assessment complete/i,
    });
    this.viewGapAnalysisButton = page.getByRole("button", {
      name: /view gap analysis/i,
    });
    this.averageProficiency = page.getByText(/average proficiency/i);
    this.scoreCards = page.locator(".rounded-lg.border.border-border.bg-card");
  }

  async goto(sessionId?: string) {
    const url = sessionId ? `/assess?session=${sessionId}` : "/assess";
    await this.page.goto(url);
  }

  async expectChatReady() {
    await expect(this.heading).toBeVisible();
    await expect(this.chatInput).toBeVisible();
  }

  async sendMessage(text: string) {
    await this.chatInput.fill(text);
    await this.sendButton.click();
  }

  async waitForResponse(timeout = 60_000) {
    // Wait for typing indicator to appear then disappear
    await this.typingIndicator
      .waitFor({ state: "visible", timeout: 10_000 })
      .catch(() => {});
    await this.typingIndicator.waitFor({ state: "hidden", timeout });
  }

  async expectProgress() {
    await expect(this.progressBar).toBeVisible();
  }

  async expectComplete() {
    await expect(this.completionHeading).toBeVisible();
  }

  async viewGapAnalysis() {
    await this.viewGapAnalysisButton.click();
  }

  async getMessageCount() {
    return this.chatMessages.count();
  }

  async retry() {
    await this.retryButton.click();
  }
}
