import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { delay, mockChat, MOCK_DELAY_MS } from "./mockChat";

describe("local Mock Chat Service", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());
  it.each([
    ["你好", "happy"],
    ["今天很累", "sad"],
    ["生气了", "angry"],
    ["哇，惊喜", "surprised"],
    ["为什么？", "curious"],
    ["随便说说", "neutral"],
  ])("returns a deterministic preset for %s", async (text, emotion) => {
    const result = mockChat(text, new AbortController().signal);
    await vi.advanceTimersByTimeAsync(MOCK_DELAY_MS);
    expect(await result).toMatchObject({ emotion, text: expect.any(String) });
  });
  it("exposes a deliberate error scenario", async () => {
    const result = mockChat("/error", new AbortController().signal);
    const assertion = expect(result).rejects.toThrow("模拟故障");
    await vi.advanceTimersByTimeAsync(MOCK_DELAY_MS);
    await assertion;
  });
  it("cancels timers both before and during a wait", async () => {
    const controller = new AbortController();
    const result = delay(1000, controller.signal);
    const assertion = expect(result).rejects.toMatchObject({
      name: "AbortError",
    });
    controller.abort();
    await assertion;
    expect(vi.getTimerCount()).toBe(0);
    await expect(delay(1000, controller.signal)).rejects.toMatchObject({
      name: "AbortError",
    });
  });
});
