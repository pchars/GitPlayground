import { test, expect } from "@playwright/test";

test("staging responds on GET /", async ({ request }) => {
  const base = process.env.BASE_URL?.replace(/\/$/, "") || "";
  test.skip(!base, "Set BASE_URL to the staging origin (e.g. https://app.example.com)");
  const res = await request.get(`${base}/`);
  expect([200, 302, 401, 403]).toContain(res.status());
});
