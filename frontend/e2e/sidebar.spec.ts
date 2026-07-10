import { test, expect } from "@playwright/test";

test.describe("Sidebar Navigation", () => {
  test("renders sidebar with Operations section", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForTimeout(2000);

    // Sidebar should be visible
    const sidebar = page.locator("aside");
    await expect(sidebar).toBeVisible();

    // Operations section
    const operations = sidebar.getByText("Operations");
    await expect(operations).toBeVisible();

    // Dashboard link in Operations section and POC Pipeline link
    const dashboardLink = sidebar.getByRole("link", { name: "Dashboard" }).last();
    await expect(dashboardLink).toBeVisible();

    const pocLink = sidebar.getByRole("link", { name: "POC Pipeline" });
    await expect(pocLink).toBeVisible();
  });

  test("navigates from dashboard to POC pipeline", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForTimeout(2000);

    // Click POC Pipeline in sidebar
    const pocLink = page.locator("aside").getByRole("link", { name: "POC Pipeline" });
    await pocLink.click();
    await page.waitForTimeout(2000);

    // Should be on POC pipeline page
    const body = page.locator("body");
    const text = await body.innerText();
    expect(text).toContain("POC Pipeline");
  });
});
