import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command, mode }) => {
  // Only read the server-only proxy setting here. Never expose NOMI_LLM_*.
  const serverEnv = loadEnv(mode, process.cwd(), "NOMI_DEV_");
  const target = serverEnv.NOMI_DEV_BACKEND_URL ?? "http://127.0.0.1:8000";
  const url = new URL(target);
  if (
    url.protocol !== "http:" ||
    !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  )
    throw new Error("NOMI_DEV_BACKEND_URL must be a loopback HTTP origin");
  return {
    base: "/Desktop-NOMI/",
    plugins: [react()],
    // Any build is Mock-only, including --mode overrides. No runtime switch in Pages.
    define: { __NOMI_PRODUCTION_MOCK__: JSON.stringify(command === "build") },
    server: { proxy: { "/api": { target: url.origin, changeOrigin: true } } },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      include: ["src/**/*.test.{ts,tsx}"],
      restoreMocks: true,
    },
  };
});
