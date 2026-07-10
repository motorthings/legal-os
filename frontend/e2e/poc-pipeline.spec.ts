import { test, expect } from "@playwright/test";

test.describe("POC Pipeline", () => {
  test("page loads", async ({ page }) => {
    await page.goto("/poc-pipeline");
    await expect(page).toHaveTitle(/Legal AI OS/i);
  });

  test("shows kanban columns", async ({ page }) => {
    await page.goto("/poc-pipeline");
    await page.waitForTimeout(3000);

    // Should show status column headers
    const body = page.locator("body");
    const text = await body.innerText();
    const hasColumns =
      text.includes("Discovery") ||
      text.includes("Build") ||
      text.includes("Review") ||
      text.includes("Graduated");
    expect(hasColumns).toBeTruthy();
  });

  test("has new POC button", async ({ page }) => {
    await page.goto("/poc-pipeline");
    await page.waitForTimeout(2000);

    const newButton = page.getByText("New POC");
    await expect(newButton).toBeVisible();
  });
});
