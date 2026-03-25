/**
 * Playwright configuration for mock-only E2E tests.
 *
 * Used when no live backend or frontend dev server is available. All API calls
 * must be intercepted via page.route() inside the test. The web server and
 * global setup (which requires a live backend) are intentionally omitted.
 *
 * Usage: npx playwright test --config playwright.mock.config.ts <spec>
 */
import { defineConfig, devices } from "@playwright/test";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e/specs",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["html", { open: "never" }], ["list"]],

  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "on-first-retry",
  },

  // No globalSetup — these tests mock all routes and need no live backend.
  // No webServer — tests are expected to run against a pre-started dev server,
  // or be fully mocked such that no real network calls escape page.route().

  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Stub auth state: no real cookies needed when all routes are mocked
        storageState: { cookies: [], origins: [] },
      },
    },
  ],
});
