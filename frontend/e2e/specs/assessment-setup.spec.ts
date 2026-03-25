import { test, expect } from "@playwright/test";
import { LandingPage } from "../pages/landing.page";

test.describe("Assessment setup", () => {
  test("selecting a role enables the start button", async ({ page }) => {
    const landing = new LandingPage(page);
    await landing.goto();
    await landing.expectLoaded();

    // Start button should be disabled initially
    await expect(landing.startButton).toBeDisabled();

    // Select a role — skills are auto-selected and start button enables
    await landing.selectRole();
    await expect(landing.startButton).toBeEnabled({ timeout: 5000 });
  });

  test("clicking start assessment navigates to /assess", async ({ page }) => {
    const landing = new LandingPage(page);
    await landing.goto();
    await landing.expectLoaded();

    await landing.selectRole();
    await expect(landing.startButton).toBeEnabled({ timeout: 5000 });

    await landing.startButton.click();
    await expect(page).toHaveURL(/\/assess/);
  });
});
