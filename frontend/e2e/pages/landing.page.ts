import { type Locator, type Page, expect } from "@playwright/test";

export class LandingPage {
  readonly page: Page;
  readonly heroHeading: Locator;
  readonly demoLink: Locator;
  readonly startButton: Locator;
  readonly roleSelector: Locator;
  readonly skillCount: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heroHeading = page.getByRole("heading", {
      name: /discover your skill gaps/i,
    });
    this.demoLink = page.getByRole("link", { name: /try interactive demo/i });
    this.startButton = page.getByRole("button", { name: /start assessment/i });
    this.roleSelector = page.getByText("Select a Role");
    this.skillCount = page.locator(".text-cyan").filter({ hasText: /^\d+$/ });
  }

  async goto() {
    await this.page.goto("/");
  }

  async expectLoaded() {
    await expect(this.heroHeading).toBeVisible();
  }

  async goToDemo() {
    await this.demoLink.click();
  }

  async selectRole(namePattern: RegExp = /engineer/i) {
    const roleCard = this.page
      .getByRole("button", { name: namePattern })
      .first();
    await expect(roleCard).toBeVisible({ timeout: 10_000 });
    await roleCard.click();
  }
}
