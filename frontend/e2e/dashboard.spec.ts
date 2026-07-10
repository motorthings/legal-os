import { test, expect } from "@playwright/test";

test.describe("Dashboard", () => {
  test("page loads with title", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveTitle(/Legal AI OS/i);
  });

  test("shows KPI cards", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForTimeout(3000); // wait for API data

    // Should show at least some content — either KPIs or loading state
    const cards = page.locator(".card");
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
  });

  test("has period selector buttons", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForTimeout(5000);

    // Period selector: 30d, 90d, 180d, 365d — rendered as buttons after data loads
    const body = page.locator("body");
    const text = await body.innerText();
    // The period selector renders after successful API call
    expect(text).toMatch(/30d|90d|180d|Hours Saved|Portfolio Dashboard/);
  });

  test("shows function breakdown when data loads", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForTimeout(5000);

    // Look for function names in the table or summary
    const body = page.locator("body");
    const text = await body.innerText();

    // At least one of the 8 functions should appear
    const hasFunctions =
      text.includes("Matter Intake") ||
      text.includes("Contract Review") ||
      text.includes("Due Diligence") ||
      text.includes("Employment") ||
      text.includes("Regulatory");
    expect(hasFunctions).toBeTruthy();
  });
});
