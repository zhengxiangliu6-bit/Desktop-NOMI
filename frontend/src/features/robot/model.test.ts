import { describe, expect, it } from "vitest";
import { initialState, robotReducer } from "./model";

describe("robot state transitions", () => {
  it("keeps interaction and emotion independent through a full turn", () => {
    const thinking = robotReducer(initialState, {
      type: "send",
      message: { id: 1, role: "user", text: "你好" },
    });
    expect(thinking).toMatchObject({ phase: "thinking", emotion: "neutral" });
    expect(
      robotReducer(thinking, {
        type: "send",
        message: { id: 2, role: "user", text: "重复" },
      }),
    ).toBe(thinking);
    const speaking = robotReducer(thinking, {
      type: "reply",
      message: { id: 2, role: "assistant", text: "你好呀" },
      emotion: "happy",
    });
    expect(speaking).toMatchObject({ phase: "speaking", emotion: "happy" });
    expect(robotReducer(speaking, { type: "settle" })).toMatchObject({
      phase: "idle",
      emotion: "neutral",
      messages: speaking.messages,
    });
  });
  it("ignores unsolicited replies, recovers errors, and bounds message history", () => {
    expect(
      robotReducer(initialState, {
        type: "reply",
        message: { id: 1, role: "assistant", text: "旧回复" },
        emotion: "sad",
      }),
    ).toBe(initialState);
    const error = robotReducer(initialState, { type: "fail", message: "故障" });
    expect(error.phase).toBe("error");
    expect(robotReducer(error, { type: "settle" })).toEqual(initialState);
    const messages = Array.from({ length: 60 }, (_, id) => ({
      id,
      role: "user" as const,
      text: "消息",
    }));
    const next = robotReducer(
      { ...initialState, messages },
      { type: "send", message: { id: 61, role: "user", text: "新消息" } },
    );
    expect(next.messages).toHaveLength(60);
    expect(next.messages[0]?.id).toBe(0);
    expect(next.pendingMessage?.text).toBe("新消息");
    const completed = robotReducer(next, {
      type: "reply",
      message: { id: 62, role: "assistant", text: "回复" },
      emotion: "happy",
    });
    expect(completed.messages).toHaveLength(60);
    expect(completed.messages[0]?.id).toBe(2);
  });
  it("locks previews even when the preview phase is idle", () => {
    const preview = robotReducer(initialState, {
      type: "preview",
      phase: "idle",
      emotion: "angry",
    });
    expect(preview).toMatchObject({
      phase: "idle",
      emotion: "angry",
      previewing: true,
    });
    expect(
      robotReducer(preview, {
        type: "send",
        message: { id: 1, role: "user", text: "消息" },
      }),
    ).toBe(preview);
  });
});
