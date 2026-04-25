import { test, expect } from "@playwright/test";

test("local login reaches profile", async ({ page }) => {
  const base = (process.env.BASE_URL || "").replace(/\/$/, "");
  test.skip(!base, "Set BASE_URL (e.g. http://127.0.0.1:8000) for authenticated smoke");
  await page.goto(`${base}/login/`);
  await page.locator("#id_username").fill("e2e_smoke");
  await page.locator("#id_password").fill("e2e-smoke-pass-2026");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page).toHaveURL(new RegExp(`${base.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/profile/e2e_smoke`));
});
