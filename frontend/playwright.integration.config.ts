import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/integration",
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5173/Desktop-NOMI/",
    headless: true,
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
      : {},
  },
  webServer: [
    {
      command:
        "uv run --directory ../backend --frozen python -m uvicorn tests.integration_server:app --host 127.0.0.1 --port 8011 --workers 1 --no-access-log",
      url: "http://127.0.0.1:8011/api/v0/health",
      reuseExistingServer: false,
      // Tests cannot inherit a real provider or key from the user's environment.
      env: {
        NOMI_LLM_PROVIDER: "mock",
        NOMI_LLM_API_KEY: "",
        NOMI_LLM_MODEL: "",
        NOMI_LLM_BASE_URL: "",
      },
    },
    {
      command: "npm run dev:api",
      url: "http://127.0.0.1:5173/Desktop-NOMI/",
      reuseExistingServer: false,
      env: {
        VITE_CHAT_MODE: "api",
        VITE_CHAT_TIMEOUT_MS: "65000",
        VITE_API_BASE_URL: "/api/v0",
        NOMI_DEV_BACKEND_URL: "http://127.0.0.1:8011",
      },
    },
  ],
});
