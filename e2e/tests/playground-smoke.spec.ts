import { test, expect } from "@playwright/test";

async function loginAsSmoke(page: import("@playwright/test").Page, base: string) {
  await page.goto(`${base}/login/`);
  await page.locator("#id_username").fill("e2e_smoke@example.com");
  await page.locator("#id_password").fill("e2e-smoke-pass-2026");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page).toHaveURL(new RegExp(`${base.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/profile/?$`));
}

test("playground run and validate smoke", async ({ page }) => {
  const base = (process.env.BASE_URL || "").replace(/\/$/, "");
  test.skip(!base, "Set BASE_URL for playground smoke");
  await loginAsSmoke(page, base);

  // Level-0 accordion may be collapsed on /tasks/; open the first unlockable task directly.
  await page.goto(`${base}/playground/gh-0_1/`);
  await expect(page).toHaveURL(/\/playground\/gh-0_1\/?$/);
  await expect(page.locator("#xterm-host")).toBeVisible();

  const csrf = await page.locator("#csrf-holder input[name=csrfmiddlewaretoken]").inputValue();
  const urls = await page.evaluate(() => (window as { __GP_PLAYGROUND__?: { urls: { run: string; validate: string } } }).__GP_PLAYGROUND__?.urls);
  expect(urls?.run).toBeTruthy();
  expect(urls?.validate).toBeTruthy();

  const runResult = await page.evaluate(
    async ({ runUrl, csrfToken }) => {
      const body = new URLSearchParams({ command: "pwd" });
      const res = await fetch(runUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRFToken": csrfToken,
        },
        body,
        credentials: "same-origin",
      });
      return { status: res.status, json: await res.json() };
    },
    { runUrl: urls!.run, csrfToken: csrf },
  );
  expect(runResult.status).toBe(200);
  expect(runResult.json.ok).toBeTruthy();

  await page.locator("#validate-btn").click();
  await expect(page.locator("#validate-output")).not.toHaveText(
    "Результат проверки появится здесь.",
    { timeout: 20000 },
  );
});
