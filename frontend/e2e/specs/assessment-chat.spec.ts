import { test, expect } from "@playwright/test";
import { AssessmentPage } from "../pages/assessment.page";
import {
  buildSSEResponse,
  buildSSEComplete,
  buildSSEError,
} from "../fixtures/mock-data";
import {
  mockAuthMe,
  mockAssessmentStart,
  mockAssessmentStartError,
  mockAssessmentRespond,
  mockAssessmentReport,
  seedAppStore,
} from "../fixtures/route-helpers";

test.describe("Assessment chat page", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthMe(page);
  });

  test("displays first question from start endpoint", async ({ page }) => {
    await mockAssessmentStart(page);
    await seedAppStore(page);
    await page.goto("/assess");

    const assess = new AssessmentPage(page);
    await assess.expectChatReady();

    // First question from mock should appear as an assistant message
    await expect(
      page.getByText(/start the assessment/i)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("sends answer and displays streamed response", async ({ page }) => {
    await mockAssessmentStart(page);
    await mockAssessmentRespond(page, [
      buildSSEResponse(
        "Good answer! Now tell me about your experience with database indexing.",
        { type: "assessment", total_questions: 1, max_questions: 25 }
      ),
    ]);
    await seedAppStore(page);
    await page.goto("/assess");

    const assess = new AssessmentPage(page);
    await assess.expectChatReady();

    // Wait for first question
    await expect(
      page.getByText(/start the assessment/i)
    ).toBeVisible({ timeout: 10_000 });

    // Send an answer
    await assess.sendMessage("I have 3 years of experience with REST APIs.");

    // User message should appear
    await expect(
      page.getByText("I have 3 years of experience with REST APIs.")
    ).toBeVisible();

    // Streamed response should appear
    await expect(
      page.getByText(/database indexing/i)
    ).toBeVisible({ timeout: 15_000 });
  });

  test("shows progress bar during assessment", async ({ page }) => {
    await mockAssessmentStart(page);
    await mockAssessmentRespond(page, [
      buildSSEResponse("Next question: explain query optimization.", {
        type: "assessment",
        total_questions: 3,
        max_questions: 25,
      }),
    ]);
    await seedAppStore(page);
    await page.goto("/assess");

    const assess = new AssessmentPage(page);
    await assess.expectChatReady();
    await expect(
      page.getByText(/start the assessment/i)
    ).toBeVisible({ timeout: 10_000 });

    // Answer and check progress updates
    await assess.sendMessage("REST APIs use HTTP methods for CRUD operations.");
    await expect(
      page.getByText(/question \d+ of ~\d+/i)
    ).toBeVisible({ timeout: 15_000 });
  });

  test("shows Assessment Complete after final response", async ({ page }) => {
    await mockAssessmentStart(page);
    await mockAssessmentRespond(page, [buildSSEComplete()]);
    await mockAssessmentReport(page);
    await seedAppStore(page);
    await page.goto("/assess");

    const assess = new AssessmentPage(page);
    await expect(
      page.getByText(/start the assessment/i)
    ).toBeVisible({ timeout: 10_000 });

    // Send final answer
    await assess.sendMessage("Here is my answer.");

    // Should transition to completion state
    await assess.expectComplete();
    await expect(assess.averageProficiency).toBeVisible();
    await expect(assess.viewGapAnalysisButton).toBeVisible();

    // Score cards should render
    const cardCount = await assess.scoreCards.count();
    expect(cardCount).toBe(3);
  });

  test("handles SSE error gracefully", async ({ page }) => {
    await mockAssessmentStart(page);
    await mockAssessmentRespond(page, [
      buildSSEError("Rate limit exceeded", 429),
    ]);
    await seedAppStore(page);
    await page.goto("/assess");

    const assess = new AssessmentPage(page);
    await expect(
      page.getByText(/start the assessment/i)
    ).toBeVisible({ timeout: 10_000 });

    await assess.sendMessage("My answer");

    // Error should be displayed
    await expect(
      page.getByText(/rate limit/i)
    ).toBeVisible({ timeout: 15_000 });
  });

  test("handles network failure on start", async ({ page }) => {
    await mockAssessmentStartError(page, 500);
    await seedAppStore(page);
    await page.goto("/assess");

    // Error display should appear
    await expect(
      page.getByText(/internal server error|failed to start/i)
    ).toBeVisible({ timeout: 15_000 });
  });

  test("redirects to / if no skills selected", async ({ page }) => {
    // Navigate without seeding store (no selected skills)
    // mockAuthMe is already set in beforeEach
    await page.goto("/assess");
    await page.waitForURL("/");
  });
});
