import { test, expect } from "@playwright/test";

async function loginAsSmoke(page: import("@playwright/test").Page, base: string) {
  await page.goto(`${base}/login/`);
  await page.locator("#id_username").fill("e2e_smoke");
  await page.locator("#id_password").fill("e2e-smoke-pass-2026");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page).toHaveURL(new RegExp(`${base.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/profile/e2e_smoke`));
}

function headerNav(page: import("@playwright/test").Page) {
  return page.getByRole("navigation", { name: "Основная навигация" });
}

test("authenticated header links reach main sections", async ({ page }) => {
  const base = (process.env.BASE_URL || "").replace(/\/$/, "");
  test.skip(!base, "Set BASE_URL for navigation smoke");
  await loginAsSmoke(page, base);

  const nav = headerNav(page);

  await nav.getByRole("link", { name: "Задачи" }).click();
  await expect(page).toHaveURL(`${base}/tasks/`);

  await nav.getByRole("link", { name: "Теория" }).click();
  await expect(page).toHaveURL(/\/theory\/\d+\//);

  await nav.getByRole("link", { name: "Квиз" }).click();
  await expect(page).toHaveURL(`${base}/quiz/`);

  await nav.getByRole("link", { name: "Таблица лидеров" }).click();
  await expect(page).toHaveURL(`${base}/leaderboard/`);
});

test("mobile nav toggle opens site menu", async ({ page }) => {
  const base = (process.env.BASE_URL || "").replace(/\/$/, "");
  test.skip(!base, "Set BASE_URL for navigation smoke");
  await page.setViewportSize({ width: 390, height: 844 });
  await loginAsSmoke(page, base);

  const toggle = page.locator("#nav-toggle");
  await expect(toggle).toBeVisible();
  await toggle.click();
  await expect(page.locator(".header.is-nav-open")).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
});
