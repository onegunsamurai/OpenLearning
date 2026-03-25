import { test, expect } from "@playwright/test";
import { TEST_USER } from "../fixtures/test-user";
import { LoginPage } from "../pages/login.page";

// These tests run in the "no-auth" project (no stored auth state)
test.use({ storageState: { cookies: [], origins: [] } });

test.describe("Authentication", () => {
  test("login page renders sign-in form", async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    await expect(loginPage.signInTab).toBeVisible();
    await expect(loginPage.registerTab).toBeVisible();
    await expect(loginPage.emailInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();
    await expect(loginPage.signInButton).toBeVisible();
    await expect(loginPage.githubButton).toBeVisible();
  });

  test("sign-in with valid credentials redirects to dashboard", async ({
    page,
  }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    // Use the test user created by global setup
    await loginPage.signIn(TEST_USER.email, TEST_USER.password);

    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("sign-in with invalid credentials shows error", async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    await loginPage.signIn("wrong@example.com", "WrongPassword123!");

    await loginPage.expectError("Invalid email or password");
  });

  test("register tab switches to registration form", async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    await loginPage.registerTab.click();

    await expect(loginPage.confirmPassword).toBeVisible();
    await expect(loginPage.registerButton).toBeVisible();
  });

  test("unauthenticated user is redirected from dashboard to login", async ({
    page,
  }) => {
    await page.goto("/dashboard");

    await expect(page).toHaveURL(/\/login/);
  });
});
