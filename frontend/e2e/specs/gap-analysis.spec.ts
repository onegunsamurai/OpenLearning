import { test, expect } from "@playwright/test";
import { GapAnalysisPage } from "../pages/gap-analysis.page";
import { MOCK_SESSION_ID, MOCK_REPORT } from "../fixtures/mock-data";
import {
  mockAuthMe,
  mockAssessmentReport,
  mockAssessmentReportDelayed,
  mockAssessmentReportError,
  seedAppStore,
} from "../fixtures/route-helpers";

test.describe("Gap Analysis page", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthMe(page);
  });

  test("shows loading state then renders report", async ({ page }) => {
    await mockAssessmentReportDelayed(page);

    const gap = new GapAnalysisPage(page);
    await gap.goto(MOCK_SESSION_ID);

    // Loading state should appear
    await gap.expectLoading();

    // Then content should render
    await gap.expectLoaded();
  });

  test("renders gap cards matching report data", async ({ page }) => {
    await mockAssessmentReport(page);

    const gap = new GapAnalysisPage(page);
    await gap.goto(MOCK_SESSION_ID);
    await gap.expectLoaded();

    const cardCount = await gap.getGapCardCount();
    expect(cardCount).toBe(MOCK_REPORT.gapAnalysis.gaps.length);

    // Verify skill names appear
    for (const g of MOCK_REPORT.gapAnalysis.gaps) {
      await expect(page.getByText(g.skillName).first()).toBeVisible();
    }
  });

  test("shows Overall Readiness heading", async ({ page }) => {
    await mockAssessmentReport(page);

    const gap = new GapAnalysisPage(page);
    await gap.goto(MOCK_SESSION_ID);
    await gap.expectLoaded();

    await expect(gap.readinessHeading).toBeVisible();
  });

  test("Generate Learning Plan navigates to /learning-plan", async ({
    page,
  }) => {
    await mockAssessmentReport(page);

    const gap = new GapAnalysisPage(page);
    await gap.goto(MOCK_SESSION_ID);
    await gap.expectLoaded();

    await gap.generateLearningPlan();
    await page.waitForURL(/\/learning-plan/);
    expect(page.url()).toContain(`session=${MOCK_SESSION_ID}`);
  });

  test("shows error state on report fetch failure", async ({ page }) => {
    await mockAssessmentReportError(page, 500);

    const gap = new GapAnalysisPage(page);
    await gap.goto(MOCK_SESSION_ID);

    await expect(
      page.getByText(/internal server error|failed to load/i)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("redirects to dashboard when no session", async ({ page }) => {
    // Navigate without session param — store also has no assessmentSessionId
    await seedAppStore(page, { assessmentSessionId: null });
    await page.goto("/gap-analysis");
    await page.waitForURL(/\/dashboard/);
  });
});
