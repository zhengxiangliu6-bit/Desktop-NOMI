// Cross-platform local API launch; no .env editing or model credentials required.
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
const child = spawn(
  process.execPath,
  [
    fileURLToPath(new URL("../node_modules/vite/bin/vite.js", import.meta.url)),
    "--host",
    "127.0.0.1",
    "--port",
    "5173",
    "--strictPort",
  ],
  {
    stdio: "inherit",
    env: {
      ...process.env,
      VITE_CHAT_MODE: "api",
      VITE_API_BASE_URL: "/api/v0",
    },
  },
);
process.once("SIGINT", () => child.kill("SIGINT"));
process.once("SIGTERM", () => child.kill("SIGTERM"));
child.once("exit", (code) => process.exit(code ?? 0));
