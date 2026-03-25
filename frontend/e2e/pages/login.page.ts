import { type Locator, type Page, expect } from "@playwright/test";

export class LoginPage {
  readonly page: Page;
  readonly signInTab: Locator;
  readonly registerTab: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly signInButton: Locator;
  readonly registerEmail: Locator;
  readonly registerPassword: Locator;
  readonly confirmPassword: Locator;
  readonly registerButton: Locator;
  readonly githubButton: Locator;
  readonly errorText: Locator;

  constructor(page: Page) {
    this.page = page;
    this.signInTab = page.getByRole("tab", { name: "Sign In" });
    this.registerTab = page.getByRole("tab", { name: "Register" });
    // Sign-in form inputs — scoped to active tab panel to avoid collisions
    const activePanel = page.locator('[data-state="active"]');
    this.emailInput = activePanel.getByPlaceholder("Email");
    this.passwordInput = activePanel.getByPlaceholder("Password").first();
    this.signInButton = activePanel.getByRole("button", { name: "Sign In" });
    // Register form inputs (also scoped to active panel)
    this.registerEmail = activePanel.getByPlaceholder("Email");
    this.registerPassword = activePanel.getByPlaceholder("Password").first();
    this.confirmPassword = page.getByPlaceholder("Confirm password");
    this.registerButton = page.getByRole("button", { name: "Create Account" });
    // OAuth
    this.githubButton = page.getByRole("button", { name: "GitHub" });
    // Error
    this.errorText = page.locator(".text-destructive");
  }

  async goto() {
    await this.page.goto("/login");
  }

  async signIn(email: string, password: string) {
    await this.signInTab.click();
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.signInButton.click();
  }

  async register(email: string, password: string) {
    await this.registerTab.click();
    await this.registerEmail.fill(email);
    await this.registerPassword.fill(password);
    await this.confirmPassword.fill(password);
    await this.registerButton.click();
  }

  async expectError(message: string) {
    await expect(this.errorText).toContainText(message);
  }
}
