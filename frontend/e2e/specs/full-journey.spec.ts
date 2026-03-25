import { test, expect } from "@playwright/test";
import { LandingPage } from "../pages/landing.page";
import { AssessmentPage } from "../pages/assessment.page";
import { GapAnalysisPage } from "../pages/gap-analysis.page";
import { LearningPlanPage } from "../pages/learning-plan.page";

const MAX_QUESTIONS = 40; // Safety limit to prevent infinite loops

test.describe.serial("Full user journey (real LLM)", () => {
  // Skip entire suite if no API key
  test.skip(
    !process.env.ANTHROPIC_API_KEY,
    "Requires ANTHROPIC_API_KEY env var"
  );

  let sessionId: string | null = null;

  test("select role on landing page and start assessment", async ({
    page,
  }) => {
    test.setTimeout(60_000);

    const landing = new LandingPage(page);
    await landing.goto();
    await landing.expectLoaded();

    // Select an engineering role
    await landing.selectRole();
    await expect(landing.startButton).toBeEnabled({ timeout: 5_000 });

    // Start assessment
    await landing.startButton.click();
    await page.waitForURL(/\/assess/, { timeout: 15_000 });
  });

  test("complete assessment chat with LLM", async ({ page }) => {
    // This test can take 10+ minutes for a full assessment
    test.setTimeout(900_000);

    // Re-select role and start (each serial test gets a fresh page)
    const landing = new LandingPage(page);
    await landing.goto();
    await landing.expectLoaded();
    await landing.selectRole();
    await expect(landing.startButton).toBeEnabled({ timeout: 5_000 });
    await landing.startButton.click();
    await page.waitForURL(/\/assess/, { timeout: 15_000 });

    const assess = new AssessmentPage(page);

    // Wait for first question to load
    await expect(assess.chatInput).toBeVisible({ timeout: 30_000 });
    await expect(assess.heading).toBeVisible();

    // Answer questions until assessment completes
    let questionCount = 0;
    while (questionCount < MAX_QUESTIONS) {
      // Check if assessment is complete
      const isComplete = await assess.completionHeading
        .isVisible()
        .catch(() => false);
      if (isComplete) break;

      // Wait for chat input to be ready
      await expect(assess.chatInput).toBeVisible({ timeout: 120_000 });
      await expect(assess.sendButton).toBeEnabled({ timeout: 5_000 });

      // Send a generic answer
      await assess.sendMessage(
        "I have moderate experience with this topic. I understand the core concepts and have applied them in production projects, including working with common patterns and best practices."
      );

      questionCount++;

      // Wait for the LLM response — either a new question or completion
      await assess.waitForResponse(120_000);

      // Wait for React to finish re-rendering before next iteration
      await expect(assess.chatInput).toBeVisible({ timeout: 10_000 }).catch(() => {});
    }

    if (questionCount >= MAX_QUESTIONS) {
      throw new Error(
        `Assessment did not complete within ${MAX_QUESTIONS} questions`
      );
    }

    // Assessment should have completed
    await assess.expectComplete();

    // Verify completion UI
    await expect(assess.averageProficiency).toBeVisible();
    await expect(assess.viewGapAnalysisButton).toBeVisible();
    const scoreCount = await assess.scoreCards.count();
    expect(scoreCount).toBeGreaterThan(0);

    // Capture session ID from the store for subsequent tests
    sessionId = await page.evaluate(() => {
      const store = sessionStorage.getItem("open-learning-store");
      if (store) {
        const parsed = JSON.parse(store);
        return parsed.state?.assessmentSessionId ?? null;
      }
      return null;
    });

    // Navigate to gap analysis
    await assess.viewGapAnalysis();
    await page.waitForURL(/\/gap-analysis/, { timeout: 15_000 });
  });

  test("view gap analysis report", async ({ page }) => {
    test.setTimeout(120_000);
    expect(sessionId, "sessionId must be set by previous test").toBeTruthy();

    const gap = new GapAnalysisPage(page);
    await gap.goto(sessionId!);

    // Wait for report to load (may take a moment to generate)
    await gap.expectLoaded();

    // Verify key elements
    await expect(gap.readinessHeading).toBeVisible();
    const cardCount = await gap.getGapCardCount();
    expect(cardCount).toBeGreaterThan(0);
    await expect(gap.generatePlanButton).toBeVisible();

    // Navigate to learning plan
    await gap.generateLearningPlan();
    await page.waitForURL(/\/learning-plan/, { timeout: 15_000 });
  });

  test("view learning plan", async ({ page }) => {
    test.setTimeout(120_000);
    expect(sessionId, "sessionId must be set by previous test").toBeTruthy();

    const plan = new LearningPlanPage(page);
    await plan.goto(sessionId!);

    // Wait for plan to load
    await plan.expectLoaded();

    // Verify key elements
    const phaseCount = await plan.getPhaseCount();
    expect(phaseCount).toBeGreaterThan(0);
    await expect(plan.exportLink).toBeVisible();
    await expect(plan.startOverButton).toBeVisible();

    // Test phase navigation if there are multiple phases
    if (phaseCount > 1) {
      await plan.selectPhase(2);
      // Verify Phase 2 content is visible
      await expect(
        page.getByRole("heading", { name: /phase 2/i })
      ).toBeVisible();
    }
  });

  test("verify content generation triggered", async ({ page }) => {
    test.setTimeout(180_000);
    expect(sessionId, "sessionId must be set by previous test").toBeTruthy();

    const apiUrl = process.env.API_URL ?? "http://localhost:8000";

    // Content pipeline runs in the background after the report is fetched.
    // Poll the materials endpoint with retries.
    const maxRetries = 12;
    const retryInterval = 10_000;
    let materials: unknown[] = [];

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      const res = await page.request.get(
        `${apiUrl}/api/materials/${sessionId}`
      );

      if (res.ok()) {
        const data = await res.json();
        const materialsArray = data?.materials ?? data;
        if (Array.isArray(materialsArray) && materialsArray.length > 0) {
          materials = materialsArray;
          break;
        }
      }

      // Wait before retrying
      if (attempt < maxRetries - 1) {
        await page.waitForTimeout(retryInterval);
      }
    }

    // Content should have been generated
    expect(materials.length).toBeGreaterThan(0);
  });
});
