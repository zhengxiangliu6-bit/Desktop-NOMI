import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useRobotController } from "./useRobotController";
import { ChatServiceError } from "../../services/chatErrors";
import { SPEAKING_MS } from "../../services/mockChat";
import type { ChatReply, ChatService } from "../../services/chatService";
const id = "00000000-0000-4000-8000-000000000001";
const reply: ChatReply = {
  text: "安全回复",
  emotion: "surprised",
  motion: "bounce",
  provider: "mock",
  sessionId: id,
};
const flush = async () => {
  await act(async () => {
    await Promise.resolve();
  });
};
describe("API controller sessions and recovery", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());
  it("saves session only on success, preserves metadata and reuses ID on next turn", async () => {
    const service = vi.fn<ChatService>().mockResolvedValue(reply);
    const { result } = renderHook(() => useRobotController(service, "api"));
    act(() => {
      result.current.send("first");
      expect(result.current.send("duplicate")).toBe(false);
    });
    expect(result.current.state.messages).toHaveLength(0);
    expect(result.current.state.pendingMessage?.text).toBe("first");
    await flush();
    expect(service.mock.calls[0]![2]).toBeUndefined();
    expect(result.current.state).toMatchObject({
      sessionId: id,
      emotion: "surprised",
      provider: "mock",
    });
    expect(result.current.state.messages[1]).toMatchObject({
      motion: "bounce",
      provider: "mock",
    });
    await act(() => vi.advanceTimersByTimeAsync(SPEAKING_MS));
    expect(result.current.state.messages).toHaveLength(2);
    act(() => {
      result.current.send("second");
    });
    await flush();
    expect(service.mock.calls[1]![2]).toBe(id);
  });
  it("preserves successful records and requires explicit new session after expiry", async () => {
    const service = vi
      .fn<ChatService>()
      .mockResolvedValueOnce(reply)
      .mockRejectedValueOnce(new ChatServiceError("SESSION_NOT_FOUND"))
      .mockResolvedValueOnce(reply);
    const { result } = renderHook(() => useRobotController(service, "api"));
    act(() => {
      result.current.send("success");
    });
    await flush();
    act(() => {
      result.current.cancel();
      result.current.send("expired");
    });
    await flush();
    expect(result.current.state.error).toContain("会话已失效");
    expect(result.current.state.messages.map((m) => m.text)).toEqual([
      "success",
      "安全回复",
    ]);
    act(() => {
      result.current.cancel();
      expect(result.current.send("blocked")).toBe(false);
    });
    act(() => {
      result.current.newConversation();
      result.current.send("fresh");
    });
    await flush();
    expect(service.mock.calls[2]![2]).toBeUndefined();
    expect(result.current.state.messages.map((m) => m.text)).toEqual([
      "fresh",
      "安全回复",
    ]);
  });
  it.each([
    "SESSION_BUSY",
    "UPSTREAM_TIMEOUT",
    "UPSTREAM_ERROR",
    "UPSTREAM_INVALID_RESPONSE",
    "CONFIGURATION_MISSING",
    "NETWORK_ERROR",
    "CLIENT_TIMEOUT",
  ] as const)(
    "recovers %s without retry or history pollution",
    async (code) => {
      const service = vi
        .fn<ChatService>()
        .mockRejectedValueOnce(new ChatServiceError(code))
        .mockResolvedValueOnce(reply);
      const { result } = renderHook(() => useRobotController(service, "api"));
      act(() => {
        result.current.send("failure");
      });
      await flush();
      expect(result.current.state.messages).toHaveLength(0);
      expect(service).toHaveBeenCalledTimes(1);
      act(() => {
        result.current.cancel();
        result.current.send("manual retry");
      });
      await flush();
      expect(result.current.state.messages.map((m) => m.text)).toEqual([
        "manual retry",
        "安全回复",
      ]);
    },
  );
  it("new conversation aborts and ignores stale session ID, emotion and text", async () => {
    let resolveOld!: (value: ChatReply) => void;
    const service = vi
      .fn<ChatService>()
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveOld = resolve;
          }),
      )
      .mockResolvedValueOnce({
        ...reply,
        sessionId: "00000000-0000-4000-8000-000000000002",
      });
    const { result } = renderHook(() => useRobotController(service, "api"));
    act(() => {
      result.current.send("old");
    });
    const signal = service.mock.calls[0]![1];
    act(() => {
      result.current.newConversation();
      result.current.send("new");
    });
    await flush();
    expect(signal.aborted).toBe(true);
    await act(async () => {
      resolveOld({ ...reply, text: "stale", emotion: "sad" });
    });
    expect(result.current.state.messages.map((m) => m.text)).toEqual([
      "new",
      "安全回复",
    ]);
    expect(result.current.state.sessionId).toBe(
      "00000000-0000-4000-8000-000000000002",
    );
    expect(result.current.state.emotion).toBe("surprised");
  });
  it("cancellation warns about unknown result; preview never sends a request", async () => {
    const service = vi
      .fn<ChatService>()
      .mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useRobotController(service, "api"));
    act(() => {
      result.current.preview("thinking", "neutral");
      result.current.cancel();
    });
    expect(result.current.state.notice).toBeNull();
    expect(service).not.toHaveBeenCalled();
    act(() => {
      result.current.send("hello");
      result.current.cancel();
    });
    expect(result.current.state.notice).toContain("不能确认后端");
    expect(result.current.state.messages).toHaveLength(0);
  });
  it("different mounted conversations never share session IDs", async () => {
    const service = vi.fn<ChatService>().mockResolvedValue(reply);
    const first = renderHook(() => useRobotController(service, "api"));
    const second = renderHook(() => useRobotController(service, "api"));
    act(() => {
      first.result.current.send("a");
    });
    await flush();
    act(() => {
      second.result.current.send("b");
    });
    await flush();
    expect(service.mock.calls.map((call) => call[2])).toEqual([
      undefined,
      undefined,
    ]);
  });
});
