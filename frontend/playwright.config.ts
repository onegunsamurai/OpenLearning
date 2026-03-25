import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3000";
const API_URL = process.env.API_URL ?? "http://localhost:8000";

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

  globalSetup: "./e2e/global-setup.ts",

  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: "e2e/.auth/user.json",
      },
      testIgnore: /.*\.noauth\.spec\.ts/,
    },
    {
      name: "no-auth",
      use: { ...devices["Desktop Chrome"] },
      testMatch: /.*\.noauth\.spec\.ts/,
    },
  ],

  webServer: [
    {
      command: `cd ${path.resolve(__dirname, "..")} && make dev-backend`,
      url: `${API_URL}/api/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npm run dev",
      url: BASE_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
});
