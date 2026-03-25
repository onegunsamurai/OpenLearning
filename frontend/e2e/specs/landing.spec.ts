import { test, expect } from "@playwright/test";
import { LandingPage } from "../pages/landing.page";

test.describe("Landing page", () => {
  test("loads with hero heading and key elements", async ({ page }) => {
    const landing = new LandingPage(page);
    await landing.goto();

    await landing.expectLoaded();
    await expect(landing.startButton).toBeVisible();
    await expect(landing.demoLink).toBeVisible();
    await expect(landing.roleSelector).toBeVisible();
  });

  test("start assessment button is disabled with no skills selected", async ({
    page,
  }) => {
    const landing = new LandingPage(page);
    await landing.goto();

    await expect(landing.startButton).toBeDisabled();
  });

  test("demo link navigates to /demo/assess", async ({ page }) => {
    const landing = new LandingPage(page);
    await landing.goto();
    await landing.goToDemo();

    await expect(page).toHaveURL(/\/demo\/assess/);
  });
});
