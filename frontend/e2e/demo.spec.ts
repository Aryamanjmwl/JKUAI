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
  const staffPassage = page.locator(".source-card").filter({ hasText: "Staff Operations" }).locator("p");
  expect(await staffPassage.evaluate((element) => element.scrollHeight <= element.clientHeight + 1)).toBe(true);
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

function textPdf(text: string): Buffer {
  const stream = `BT /F1 12 Tf 50 700 Td (${text}) Tj ET`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let content = "%PDF-1.4\n";
  const offsets = [0];
  for (const [index, object] of objects.entries()) {
    offsets.push(Buffer.byteLength(content));
    content += `${index + 1} 0 obj\n${object}\nendobj\n`;
  }
  const xref = Buffer.byteLength(content);
  content += `xref\n0 6\n0000000000 65535 f \n${offsets.slice(1).map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`).join("")}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(content);
}

test("a reviewer can upload a PDF from the page and retrieve its content", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Simulated role").selectOption("");
  await page.getByRole("button", { name: "Add PDF", exact: true }).click();
  await page.getByLabel("PDF file").setInputFiles({
    name: "browser-upload.pdf", mimeType: "application/pdf",
    buffer: textPdf("The NOVA lab accepts bookings every Tuesday. This is fictional browser-test data."),
  });
  await page.getByLabel("Document title", { exact: true }).fill("Browser Uploaded Lab Guide");
  await page.getByRole("button", { name: "Upload PDF", exact: true }).click();
  await expect(page.locator(".upload-success")).toContainText("You can search it now.", { timeout: 120_000 });
  await page.getByRole("button", { name: "Upload PDF", exact: true }).click();
  await expect(page.locator(".upload-success")).toContainText("already indexed");
  await page.screenshot({ path: "test-results/document-upload.png", fullPage: true });
  await page.getByRole("button", { name: "Close upload", exact: true }).click();
  await page.getByLabel("Your question").fill("When can I book the NOVA lab?");
  await page.locator("form.search-form").getByRole("button", { name: "Search sources" }).click();
  await expect(page.locator(".source-card").first()).toContainText("Browser Uploaded Lab Guide");
  await expect(page.locator(".source-card").first()).toContainText("Tuesday");
});
