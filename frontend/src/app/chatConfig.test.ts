import { describe, expect, it } from "vitest";
import { readChatConfig } from "./chatConfig";
describe("chat mode boundary", () => {
  it("defaults to mock and allows explicit local API development", () => {
    expect(readChatConfig({}, false).mode).toBe("mock");
    expect(readChatConfig({ VITE_CHAT_MODE: "api" }, false)).toMatchObject({
      mode: "api",
      baseUrl: "/api/v0",
    });
  });
  it("forces production Mock even with API settings", () => {
    expect(
      readChatConfig(
        {
          VITE_CHAT_MODE: "api",
          VITE_API_BASE_URL: "https://untrusted.example",
        },
        true,
      ).mode,
    ).toBe("mock");
  });
  it.each([
    { VITE_CHAT_MODE: "unknown" },
    { VITE_API_BASE_URL: "https://api.example/v0" },
    { VITE_CHAT_TIMEOUT_MS: "0" },
  ])("rejects unsafe development config", (env) => {
    expect(() => readChatConfig(env, false)).toThrow();
  });
});
