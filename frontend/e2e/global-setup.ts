import { chromium, type FullConfig } from "@playwright/test";
import { TEST_USER } from "./fixtures/test-user";

async function globalSetup(config: FullConfig) {
  const baseURL = process.env.BASE_URL ?? "http://localhost:3000";
  const apiURL = process.env.API_URL ?? "http://localhost:8000";

  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL });
  const page = await context.newPage();

  // Register test user (ignore 409 if already exists)
  const registerRes = await page.request.post(`${apiURL}/api/auth/register`, {
    data: { email: TEST_USER.email, password: TEST_USER.password },
  });

  if (!registerRes.ok() && registerRes.status() !== 409) {
    await browser.close();
    throw new Error(
      `Failed to register test user: ${registerRes.status()} ${await registerRes.text()}`
    );
  }

  if (registerRes.status() === 409) {
    // User already exists — log in instead
    const loginRes = await page.request.post(`${apiURL}/api/auth/login`, {
      data: { email: TEST_USER.email, password: TEST_USER.password },
    });

    if (!loginRes.ok()) {
      await browser.close();
      throw new Error(
        `Failed to login test user: ${loginRes.status()} ${await loginRes.text()}`
      );
    }
  }

  // Set API key for the test user if available (required for real LLM tests)
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (apiKey) {
    const keyRes = await page.request.post(`${apiURL}/api/auth/api-key`, {
      data: { apiKey },
    });
    if (!keyRes.ok() && keyRes.status() !== 409) {
      throw new Error(
        `Failed to set API key for test user: ${keyRes.status()} ${await keyRes.text()}`
      );
    }
  }

  // Navigate to let the browser pick up the auth cookie
  await page.goto("/dashboard");
  await context.storageState({ path: "e2e/.auth/user.json" });
  await browser.close();
}

export default globalSetup;
