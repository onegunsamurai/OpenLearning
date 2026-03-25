import type { Page } from "@playwright/test";
import {
  MOCK_AUTH_ME,
  MOCK_START_RESPONSE,
  MOCK_REPORT,
  MOCK_STORE_STATE,
} from "./mock-data";
import type { AssessmentReportResponse } from "../../src/lib/api";

const LOADING_DELAY_MS = 500;

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

/** Intercept GET /api/auth/me to return a user with hasApiKey: true. */
export async function mockAuthMe(
  page: Page,
  overrides?: Record<string, unknown>
) {
  await page.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ...MOCK_AUTH_ME, ...overrides }),
    });
  });
}

// ---------------------------------------------------------------------------
// Assessment
// ---------------------------------------------------------------------------

/** Intercept POST /api/assessment/start. */
export async function mockAssessmentStart(
  page: Page,
  response = MOCK_START_RESPONSE
) {
  await page.route("**/api/assessment/start", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(response),
      });
    } else {
      await route.fallback();
    }
  });
}

/**
 * Intercept POST /api/assessment/{id}/respond with sequential SSE responses.
 * Each call returns the next response in the array. After exhausting the array
 * it keeps returning the last response.
 */
export async function mockAssessmentRespond(
  page: Page,
  sseResponses: string[]
) {
  let callIndex = 0;
  await page.route("**/api/assessment/*/respond", async (route) => {
    if (route.request().method() === "POST") {
      const idx = Math.min(callIndex++, sseResponses.length - 1);
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: {
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
        body: sseResponses[idx],
      });
    } else {
      await route.fallback();
    }
  });
}

/** Intercept GET /api/assessment/{id}/report. */
export async function mockAssessmentReport(
  page: Page,
  report: AssessmentReportResponse = MOCK_REPORT
) {
  await page.route("**/api/assessment/*/report", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(report),
      });
    } else {
      await route.fallback();
    }
  });
}

/** Intercept GET /api/assessment/{id}/report with an error. */
export async function mockAssessmentReportError(page: Page, status = 500) {
  await page.route("**/api/assessment/*/report", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }),
      });
    } else {
      await route.fallback();
    }
  });
}

/** Intercept GET /api/assessment/{id}/report with a delayed response (for loading state tests). */
export async function mockAssessmentReportDelayed(
  page: Page,
  report: AssessmentReportResponse = MOCK_REPORT,
  delayMs = LOADING_DELAY_MS
) {
  await page.route("**/api/assessment/*/report", async (route) => {
    if (route.request().method() === "GET") {
      await new Promise((r) => setTimeout(r, delayMs));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(report),
      });
    } else {
      await route.fallback();
    }
  });
}

/** Intercept POST /api/assessment/start with an error. */
export async function mockAssessmentStartError(page: Page, status = 500) {
  await page.route("**/api/assessment/start", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }),
      });
    } else {
      await route.fallback();
    }
  });
}

// ---------------------------------------------------------------------------
// Store seeding
// ---------------------------------------------------------------------------

/**
 * Navigate to the app domain and seed the Zustand sessionStorage store.
 * Must be called before navigating to pages that depend on store state.
 */
export async function seedAppStore(
  page: Page,
  overrides?: Partial<(typeof MOCK_STORE_STATE)["state"]>
) {
  // Need to be on the domain before setting sessionStorage
  await page.goto("/");
  const storeValue = {
    ...MOCK_STORE_STATE,
    state: { ...MOCK_STORE_STATE.state, ...overrides },
  };
  await page.evaluate((val) => {
    sessionStorage.setItem("open-learning-store", JSON.stringify(val));
  }, storeValue);
}
