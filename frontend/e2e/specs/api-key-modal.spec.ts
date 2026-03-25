import { test, expect } from "@playwright/test";
import { mockAuthMe } from "../fixtures/route-helpers";

test.describe("API Key Modal", () => {
  test.beforeEach(async ({ page }) => {
    // Mock user with no API key to trigger auto-prompt
    await mockAuthMe(page, { hasApiKey: false });

    // Mock the API key GET endpoint — 204 No Content (no key stored)
    await page.route("**/api/auth/api-key", async (route) => {
      await route.fulfill({
        status: 204,
        body: "",
      });
    });
  });

  test("can be dismissed via Skip for now button", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Set Up Your API Key")).toBeVisible();

    await page.getByText("Skip for now").click();

    await expect(page.getByText("Set Up Your API Key")).not.toBeVisible();
  });

  test("can be dismissed via X close button", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Set Up Your API Key")).toBeVisible();

    await page.getByLabel("Close").click();

    await expect(page.getByText("Set Up Your API Key")).not.toBeVisible();
  });
});
