import { test, expect } from "@playwright/test";
import { DashboardPage } from "../pages/dashboard.page";

test.describe("Dashboard", () => {
  test("loads and displays key elements for authenticated user", async ({
    page,
  }) => {
    const dashboard = new DashboardPage(page);
    await dashboard.goto();

    await dashboard.expectLoaded();
    await expect(dashboard.newAssessmentButton).toBeVisible();
  });

  test("new assessment button navigates to landing page", async ({ page }) => {
    const dashboard = new DashboardPage(page);
    await dashboard.goto();
    await dashboard.expectLoaded();

    await dashboard.startNewAssessment();

    await expect(page).toHaveURL("/");
  });

  test("shows empty state or assessment cards", async ({ page }) => {
    const dashboard = new DashboardPage(page);
    await dashboard.goto();
    await dashboard.expectLoaded();

    // Either empty state or assessment cards should be visible
    const hasEmptyState = await dashboard.emptyState.isVisible();
    const cardCount = await dashboard.assessmentCards.count();
    expect(hasEmptyState || cardCount > 0).toBeTruthy();
  });
});
