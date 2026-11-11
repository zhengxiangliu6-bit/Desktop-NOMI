import { afterEach, describe, expect, it, vi } from "vitest";
import { createHttpChatService } from "./httpChat";
import { errorStatuses } from "../api/contract";
const id = "00000000-0000-4000-8000-000000000001";
const response = {
  reply: "你好",
  emotion: "surprised",
  motion: "bounce",
  provider: "mock",
  session_id: id,
};
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
afterEach(() => vi.useRealTimers());
describe("HTTP Chat Service", () => {
  it("sends only text and optional session ID; returns validated metadata", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json(response))
      .mockResolvedValueOnce(json(response));
    const service = createHttpChatService({ fetcher });
    expect(await service(" hello ", new AbortController().signal)).toEqual({
      text: "你好",
      emotion: "surprised",
      motion: "bounce",
      provider: "mock",
      sessionId: id,
    });
    await service("again", new AbortController().signal, id);
    expect(JSON.parse(fetcher.mock.calls[0]![1]!.body as string)).toEqual({
      text: "hello",
    });
    expect(JSON.parse(fetcher.mock.calls[1]![1]!.body as string)).toEqual({
      text: "again",
      session_id: id,
    });
    expect(fetcher.mock.calls[0]![0]).toBe("/api/v0/chat");
    expect(fetcher.mock.calls[0]![1]!.credentials).toBe("omit");
  });
  it.each(Object.entries(errorStatuses))(
    "maps %s without rendering upstream detail",
    async (code, statuses) => {
      const service = createHttpChatService({
        fetcher: vi
          .fn<typeof fetch>()
          .mockResolvedValue(
            json(
              {
                error: {
                  code,
                  message: "sensitive-test-detail",
                  request_id: id,
                  retryable: true,
                },
              },
              statuses[0],
            ),
          ),
      });
      try {
        await service("hello", new AbortController().signal);
        throw Error("unexpected success");
      } catch (error) {
        expect(error).toMatchObject({ code });
        expect(String(error)).not.toContain("sensitive-test-detail");
      }
    },
  );
  it.each([
    { ...response, emotion: "unrecognized" },
    { ...response, motion: { command: "shell" } },
    { ...response, reply: " " },
    { ...response, reply: 123 },
    { ...response, reply: "a".repeat(8001) },
    { ...response, session_id: "bad" },
    { ...response, provider: "unknown" },
    {},
  ])("rejects malformed success", async (value) => {
    const service = createHttpChatService({
      fetcher: vi.fn<typeof fetch>().mockResolvedValue(json(value)),
    });
    await expect(
      service("hi", new AbortController().signal),
    ).rejects.toMatchObject({ code: "INVALID_RESPONSE" });
  });
  it("rejects non JSON, invalid JSON and session replacement", async () => {
    for (const value of [
      new Response("<html>private-error</html>"),
      new Response("{", { headers: { "Content-Type": "application/json" } }),
      json({ ...response, session_id: "00000000-0000-4000-8000-000000000002" }),
    ]) {
      const service = createHttpChatService({
        fetcher: vi.fn<typeof fetch>().mockResolvedValue(value),
      });
      await expect(
        service("hi", new AbortController().signal, id),
      ).rejects.toMatchObject({ code: "INVALID_RESPONSE" });
    }
  });
  it("reports backend unavailable and never retries", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockRejectedValue(new TypeError("private-url-or-network-details"));
    await expect(
      createHttpChatService({ fetcher })("hi", new AbortController().signal),
    ).rejects.toMatchObject({ code: "NETWORK_ERROR" });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it("aborts a request and clears timeout listeners", async () => {
    const fetcher = vi.fn<typeof fetch>().mockImplementation(
      (_url, options) =>
        new Promise((_resolve, reject) => {
          options!.signal!.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          );
        }),
    );
    const controller = new AbortController();
    const promise = createHttpChatService({ fetcher })("hi", controller.signal);
    const assertion = expect(promise).rejects.toMatchObject({
      name: "AbortError",
    });
    controller.abort();
    await assertion;
    expect(fetcher.mock.calls[0]![1]!.signal!.aborted).toBe(true);
  });
  it("distinguishes deadline from user cancellation", async () => {
    vi.useFakeTimers();
    const fetcher = vi.fn<typeof fetch>().mockImplementation(
      (_url, options) =>
        new Promise((_resolve, reject) => {
          options!.signal!.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          );
        }),
    );
    const promise = createHttpChatService({ fetcher, timeoutMs: 20 })(
      "hi",
      new AbortController().signal,
    );
    const assertion = expect(promise).rejects.toMatchObject({
      code: "CLIENT_TIMEOUT",
    });
    await vi.advanceTimersByTimeAsync(20);
    await assertion;
    expect(vi.getTimerCount()).toBe(0);
  });
});
