import { StrictMode, type ReactNode } from "react";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  MOCK_DELAY_MS,
  PREVIEW_MS,
  SPEAKING_MS,
  type ChatReply,
  type ChatService,
} from "../../services/mockChat";
import { useRobotController } from "./useRobotController";

const wrapper = ({ children }: { children: ReactNode }) => (
  <StrictMode>{children}</StrictMode>
);
describe("robot controller lifecycle", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());
  it("rejects blank, oversized and same-tick duplicate submissions; settles after reply", async () => {
    const { result } = renderHook(() => useRobotController(), { wrapper });
    act(() => {
      expect(result.current.send("   ")).toBe(false);
      expect(result.current.send("a".repeat(4001))).toBe(false);
      expect(result.current.send("你好")).toBe(true);
      expect(result.current.send("重复")).toBe(false);
    });
    expect(result.current.state.phase).toBe("thinking");
    await act(() => vi.advanceTimersByTimeAsync(MOCK_DELAY_MS));
    expect(result.current.state).toMatchObject({
      phase: "speaking",
      emotion: "happy",
    });
    expect(result.current.state.messages).toHaveLength(2);
    await act(() => vi.advanceTimersByTimeAsync(SPEAKING_MS));
    expect(result.current.state).toMatchObject({
      phase: "idle",
      emotion: "neutral",
    });
  });
  it("recovers from a service error and can start a new turn", async () => {
    const { result } = renderHook(() => useRobotController(), { wrapper });
    act(() => {
      result.current.send("/error");
    });
    await act(() => vi.advanceTimersByTimeAsync(MOCK_DELAY_MS));
    expect(result.current.state.phase).toBe("error");
    act(() => {
      expect(result.current.send("你好")).toBe(false);
      result.current.cancel();
    });
    expect(result.current.state.error).toBeNull();
    act(() => {
      expect(result.current.send("你好")).toBe(true);
    });
    await act(() => vi.advanceTimersByTimeAsync(MOCK_DELAY_MS + SPEAKING_MS));
    expect(result.current.state.phase).toBe("idle");
  });
  it("ignores a late reply even if a service ignores cancellation", async () => {
    let resolveOld!: (reply: ChatReply) => void;
    const service: ChatService = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<ChatReply>((resolve) => {
            resolveOld = resolve;
          }),
      )
      .mockResolvedValue({
        text: "新回复",
        emotion: "happy",
        motion: "none",
        provider: "frontend-mock",
      });
    const { result } = renderHook(() => useRobotController(service), {
      wrapper,
    });
    act(() => {
      result.current.send("旧消息");
      result.current.cancel();
      result.current.send("新消息");
    });
    await act(async () => {
      await Promise.resolve();
    });
    await act(async () => {
      resolveOld({
        text: "过期回复",
        emotion: "sad",
        motion: "none",
        provider: "frontend-mock",
      });
    });
    expect(result.current.state.messages.map((m) => m.text)).toEqual([
      "新消息",
      "新回复",
    ]);
    expect(result.current.state.emotion).toBe("happy");
  });
  it("aborts pending timers on unmount and accepts no post-unmount submission", async () => {
    const { result, unmount } = renderHook(() => useRobotController(), {
      wrapper,
    });
    act(() => {
      result.current.send("你好");
    });
    unmount();
    await act(async () => {
      await Promise.resolve();
    });
    expect(vi.getTimerCount()).toBe(0);
    expect(result.current.send("已卸载")).toBe(false);
  });
  it("locks preview interaction and clears previews on timeout or cancel", async () => {
    const { result } = renderHook(() => useRobotController(), { wrapper });
    act(() => {
      result.current.preview("listening", "neutral");
      expect(result.current.send("重复")).toBe(false);
    });
    expect(result.current.state.phase).toBe("listening");
    await act(() => vi.advanceTimersByTimeAsync(PREVIEW_MS));
    expect(result.current.state.phase).toBe("idle");
    act(() => {
      result.current.preview("idle", "angry");
    });
    expect(result.current.busy).toBe(true);
    act(() => {
      result.current.cancel();
    });
    expect(result.current.state).toMatchObject({
      phase: "idle",
      emotion: "neutral",
      previewing: false,
    });
    expect(vi.getTimerCount()).toBe(0);
  });
  it("cancels speaking completion and prevents it from settling a new request", async () => {
    const { result } = renderHook(() => useRobotController(), { wrapper });
    act(() => {
      result.current.send("你好");
    });
    await act(() => vi.advanceTimersByTimeAsync(MOCK_DELAY_MS));
    act(() => {
      result.current.cancel();
      result.current.send("今天很累");
    });
    await act(() => vi.advanceTimersByTimeAsync(MOCK_DELAY_MS));
    expect(result.current.state).toMatchObject({
      phase: "speaking",
      emotion: "sad",
    });
    await act(() => vi.advanceTimersByTimeAsync(SPEAKING_MS));
    expect(result.current.state.phase).toBe("idle");
  });
});
