import { test, expect } from "@playwright/test";

test("public landing shows learning hero and CTA", async ({ page }) => {
  const base = (process.env.BASE_URL || "").replace(/\/$/, "");
  test.skip(!base, "Set BASE_URL (e.g. http://127.0.0.1:8000) for landing smoke");
  await page.goto(`${base}/`);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText("Что такое Git")).toBeVisible();
  await expect(page.getByText("Готов прокачать Git на практике?")).toBeVisible();
  await expect(page.locator(".landing-hero-full")).toBeVisible();
});
