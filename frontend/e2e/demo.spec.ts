import { expect, test } from "@playwright/test";

test("a fresh reviewer can retrieve sources and inspect permission isolation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "What would you like to know?" })).toBeVisible();
  await expect(page.getByLabel("OpenAI API key", { exact: true })).toHaveCount(0);
  await page.getByLabel("Simulated role").selectOption("");
  await page.getByLabel("Your question").fill("What do I need before taking Advanced Machine Learning?");
  await page.locator("form.search-form").getByRole("button", { name: "Search sources" }).click();
  await expect(page.locator(".source-card").filter({ hasText: "Course Guide" })).toBeVisible();
  await expect(page.locator(".source-card").filter({ hasText: "Course Guide" })).toContainText("Linear Algebra");

  await page.getByLabel("Your question").fill("What is the EXAM-OPS-42 internal routing code?");
  await page.locator("form.search-form").getByRole("button", { name: "Search sources" }).click();
  await expect(page.getByRole("heading", { name: "Ranked source passages" })).toBeVisible();
  await expect(page.locator(".source-card").filter({ hasText: "Staff Operations" })).toHaveCount(0);
  await expect(page.locator(".results")).not.toContainText("ORCHID-742");

  await page.getByLabel("Simulated role").selectOption("staff");
  await expect(page.locator(".results")).toHaveCount(0);
  await page.locator("form.search-form").getByRole("button", { name: "Search sources" }).click();
  await expect(page.locator(".source-card").filter({ hasText: "Staff Operations" })).toContainText("ORCHID-742");
  await page.screenshot({ path: "test-results/staff-source-search.png", fullPage: true });

  await page.getByRole("button", { name: "Answer with citations" }).click();
  await expect(page.getByLabel("OpenAI API key", { exact: true })).toBeVisible();
  await expect(page.locator(".results")).toHaveCount(0);
});

test("source search fits a phone viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByLabel("Your question")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/mobile-start.png", fullPage: true });
});
