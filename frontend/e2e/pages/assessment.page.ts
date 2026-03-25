import { type Locator, type Page, expect } from "@playwright/test";

export class AssessmentPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly chatInput: Locator;
  readonly sendButton: Locator;
  readonly chatMessages: Locator;
  readonly typingIndicator: Locator;
  readonly progressBar: Locator;
  readonly errorDisplay: Locator;
  readonly retryButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole("heading", { name: /skill assessment/i });
    this.chatInput = page.getByPlaceholder("Type your answer...");
    this.sendButton = page.locator('button[type="submit"]');
    this.chatMessages = page.locator("[class*=space-y] > div");
    this.typingIndicator = page.locator("[class*=typing], [class*=animate-pulse]");
    this.progressBar = page.locator('[role="progressbar"]');
    this.errorDisplay = page.locator("[class*=alert], [class*=error]");
    this.retryButton = page.getByRole("button", { name: /retry/i });
  }

  async goto(sessionId?: string) {
    const url = sessionId ? `/assess?session=${sessionId}` : "/assess";
    await this.page.goto(url);
  }

  async sendMessage(text: string) {
    await this.chatInput.fill(text);
    await this.sendButton.click();
  }

  async waitForResponse() {
    // Wait for typing indicator to appear then disappear
    await this.typingIndicator.waitFor({ state: "visible", timeout: 10_000 }).catch(() => {});
    await this.typingIndicator.waitFor({ state: "hidden", timeout: 60_000 });
  }

  async expectProgress() {
    await expect(this.progressBar).toBeVisible();
  }

  async retry() {
    await this.retryButton.click();
  }
}
