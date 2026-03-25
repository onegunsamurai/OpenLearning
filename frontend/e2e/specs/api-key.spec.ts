import { test, expect } from "@playwright/test";
import { mockAuthMe } from "../fixtures/route-helpers";

/**
 * Regression tests for GET /api/auth/api-key returning 204 (not 404) when no
 * API key is stored.
 *
 * Before the fix the backend returned 404, which caused a browser console error:
 * "[ERROR] Failed to load resource: the server responded with a status of 404"
 *
 * After the fix the backend returns 204 No Content, which the frontend
 * api.authGetApiKey() handles by returning null — no error, no console noise.
 */

test.describe("GET /api/auth/api-key — 204 when no key is stored", () => {
  test.beforeEach(async ({ page }) => {
    // Authenticated user who has not yet set an API key
    await mockAuthMe(page, { hasApiKey: false });

    // Mock the fixed backend: 204 No Content (no body)
    await page.route("**/api/auth/api-key", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 204,
          body: "",
        });
      } else {
        await route.fallback();
      }
    });
  });

  test("GET /api/auth/api-key returns 204 and no 404 console errors appear", async ({
    page,
  }) => {
    const consoleErrors: string[] = [];

    // Capture all console errors so we can assert none relate to api-key 404
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    // Capture all page-level errors (uncaught exceptions)
    const pageErrors: string[] = [];
    page.on("pageerror", (err) => {
      pageErrors.push(err.message);
    });

    // Intercept the network request to assert the status code
    const apiKeyRequestPromise = page.waitForRequest(
      (req) =>
        req.url().includes("/api/auth/api-key") && req.method() === "GET"
    );

    // Navigate to the landing page — PageShell renders with autoPromptApiKey=true
    // which triggers ApiKeySetup to open (hasApiKey: false) and calls authGetApiKey()
    await page.goto("/");

    // Wait for the api-key network request to be made
    const apiKeyRequest = await apiKeyRequestPromise;
    const apiKeyResponse = await apiKeyRequest.response();

    // Primary assertion: the mocked (and post-fix real) response is 204
    expect(apiKeyResponse).not.toBeNull();
    expect(apiKeyResponse!.status()).toBe(204);

    // The API key setup modal should be visible (auto-prompted for hasApiKey: false)
    await expect(page.getByText("Set Up Your API Key")).toBeVisible();

    // No "Current key" preview section should appear — 204 means no key stored
    await expect(
      page.getByText("Current key")
    ).not.toBeVisible();

    // Assert no 404 console errors related to api-key appeared
    const apiKey404Errors = consoleErrors.filter(
      (msg) =>
        msg.includes("404") &&
        (msg.toLowerCase().includes("api-key") ||
          msg.toLowerCase().includes("api/auth"))
    );
    expect(
      apiKey404Errors,
      `Expected no 404 console errors for api-key, but got: ${JSON.stringify(apiKey404Errors)}`
    ).toHaveLength(0);

    // Assert no uncaught page errors from the api-key fetch path
    const apiKeyPageErrors = pageErrors.filter(
      (msg) =>
        msg.toLowerCase().includes("api-key") ||
        (msg.includes("404") && msg.toLowerCase().includes("auth"))
    );
    expect(
      apiKeyPageErrors,
      `Expected no uncaught page errors for api-key, but got: ${JSON.stringify(apiKeyPageErrors)}`
    ).toHaveLength(0);
  });

  test("204 response results in null preview — modal shows no existing key UI", async ({
    page,
  }) => {
    await page.goto("/");

    // Modal auto-opens for users without a key
    await expect(page.getByText("Set Up Your API Key")).toBeVisible();

    // With a 204 (no key stored), the preview section must be absent
    await expect(page.getByText("Current key")).not.toBeVisible();
    await expect(page.getByLabel("Remove API key")).not.toBeVisible();

    // The primary CTA should read "Validate & Save", not "Update Key"
    await expect(
      page.getByRole("button", { name: "Validate & Save" })
    ).toBeVisible();
  });

  test("204 response does not cause the modal to show a stale or broken state", async ({
    page,
  }) => {
    await page.goto("/");

    await expect(page.getByText("Set Up Your API Key")).toBeVisible();

    // Modal should be fully interactive after a 204 — user can type a key.
    // Use the textbox role to disambiguate from other elements with "API key"
    // in their aria-label (the header icon button, the show/hide toggle, etc.)
    const apiKeyInput = page.getByRole("textbox", { name: "API key" });
    await expect(apiKeyInput).toBeVisible();
    await apiKeyInput.fill("sk-ant-test-key");

    // The save button should become enabled once input is non-empty
    await expect(
      page.getByRole("button", { name: "Validate & Save" })
    ).toBeEnabled();

    // User can dismiss without errors
    await page.getByText("Skip for now").click();
    await expect(page.getByText("Set Up Your API Key")).not.toBeVisible();
  });
});
