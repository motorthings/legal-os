import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 3,
  timeout: 30_000,
  reporter: "html",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // To test locally:
  //   1. Start backend: cd backend && DEMO_MODE=true python start.py
  //   2. Start frontend: cd frontend && npm run dev
  //   3. Run tests:  npx playwright test
  webServer: process.env.CI ? [] : [
    {
      command: "cd .. && cd backend && DEMO_MODE=true /opt/homebrew/bin/python3 start.py",
      port: 8080,
      timeout: 15_000,
      reuseExistingServer: true,
    },
    {
      command: "npm run dev",
      port: 3000,
      timeout: 30_000,
      reuseExistingServer: true,
    },
  ],
});
