import { test, expect } from "@playwright/test";
import { LearningPlanPage } from "../pages/learning-plan.page";
import { MOCK_SESSION_ID, MOCK_REPORT } from "../fixtures/mock-data";
import {
  mockAuthMe,
  mockAssessmentReport,
  mockAssessmentReportDelayed,
  mockAssessmentReportError,
} from "../fixtures/route-helpers";

test.describe("Learning Plan page", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthMe(page);
  });

  test("shows loading state then renders plan", async ({ page }) => {
    await mockAssessmentReportDelayed(page);

    const plan = new LearningPlanPage(page);
    await plan.goto(MOCK_SESSION_ID);

    await plan.expectLoading();
    await plan.expectLoaded();
  });

  test("renders phase navigation buttons", async ({ page }) => {
    await mockAssessmentReport(page);

    const plan = new LearningPlanPage(page);
    await plan.goto(MOCK_SESSION_ID);
    await plan.expectLoaded();

    const phaseCount = await plan.getPhaseCount();
    expect(phaseCount).toBe(MOCK_REPORT.learningPlan.phases.length);

    // Phase titles should be visible
    for (const phase of MOCK_REPORT.learningPlan.phases) {
      await expect(
        page.getByText(phase.title, { exact: false }).first()
      ).toBeVisible();
    }
  });

  test("phase navigation switches content", async ({ page }) => {
    await mockAssessmentReport(page);

    const plan = new LearningPlanPage(page);
    await plan.goto(MOCK_SESSION_ID);
    await plan.expectLoaded();

    // Click Phase 2
    await plan.selectPhase(2);

    // Phase 2 content should be visible
    const phase2Title = MOCK_REPORT.learningPlan.phases[1].title;
    await expect(
      page.getByRole("heading", { name: new RegExp(phase2Title, "i") })
    ).toBeVisible();
  });

  test("copy button shows copied feedback", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await mockAssessmentReport(page);

    const plan = new LearningPlanPage(page);
    await plan.goto(MOCK_SESSION_ID);
    await plan.expectLoaded();

    await plan.copyButton.click();
    await expect(page.getByText("Copied!")).toBeVisible();
  });

  test("export link has correct href", async ({ page }) => {
    await mockAssessmentReport(page);

    const plan = new LearningPlanPage(page);
    await plan.goto(MOCK_SESSION_ID);
    await plan.expectLoaded();

    const href = await plan.exportLink.getAttribute("href");
    expect(href).toContain(`/export/${MOCK_SESSION_ID}`);
  });

  test("Start Over navigates to landing", async ({ page }) => {
    await mockAssessmentReport(page);

    const plan = new LearningPlanPage(page);
    await plan.goto(MOCK_SESSION_ID);
    await plan.expectLoaded();

    await plan.startOver();
    await page.waitForURL("/");
  });

  test("shows error state on fetch failure", async ({ page }) => {
    await mockAssessmentReportError(page, 500);

    const plan = new LearningPlanPage(page);
    await plan.goto(MOCK_SESSION_ID);

    await expect(
      page.getByText(/internal server error|failed to load/i)
    ).toBeVisible({ timeout: 10_000 });
  });
});
