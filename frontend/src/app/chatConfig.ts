import type { ChatMode } from "../services/chatService";
import { validateApiBase } from "../services/httpChat";
export interface ChatConfig {
  mode: ChatMode;
  baseUrl: string;
  timeoutMs: number;
}
export function readChatConfig(
  env: Record<string, string | undefined>,
  production: boolean,
): ChatConfig {
  // Production artifacts are always frontend Mock, regardless of mode/env/query settings.
  if (production) return { mode: "mock", baseUrl: "/api/v0", timeoutMs: 65000 };
  const mode = env.VITE_CHAT_MODE ?? "mock";
  if (mode !== "api" && mode !== "mock")
    throw new Error("VITE_CHAT_MODE must be mock or api");
  const timeoutMs = Number(env.VITE_CHAT_TIMEOUT_MS ?? 65000);
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1000 || timeoutMs > 125000)
    throw new Error("VITE_CHAT_TIMEOUT_MS must be 1000..125000");
  return {
    mode,
    baseUrl: validateApiBase(env.VITE_API_BASE_URL ?? "/api/v0"),
    timeoutMs,
  };
}
