import { test, expect } from "@playwright/test";

test.describe("Sidebar Navigation", () => {
  test("renders sidebar with the default (attorney) persona groups", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForTimeout(2000);

    // Sidebar should be visible
    const sidebar = page.locator("aside");
    await expect(sidebar).toBeVisible();

    // Default persona is "attorney": groups are Practice and Tools.
    await expect(sidebar.getByText("Practice", { exact: true })).toBeVisible();
    await expect(sidebar.getByText("Tools", { exact: true })).toBeVisible();

    // A known link in each group.
    await expect(sidebar.getByRole("link", { name: "Employment" })).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Legal Research" })).toBeVisible();
  });

  test("navigates from the sidebar to a function page", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForTimeout(2000);

    // Click Contract Review in the sidebar (Tools group, default persona).
    const link = page.locator("aside").getByRole("link", { name: "Contract Review" });
    await link.click();
    await page.waitForURL("**/contract-review", { timeout: 10_000 });

    expect(page.url()).toContain("/contract-review");
  });
});
