import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  use: {
    baseURL: process.env.BASE_URL || "",
    trace: "on-first-retry",
  },
  retries: process.env.CI ? 1 : 0,
});
