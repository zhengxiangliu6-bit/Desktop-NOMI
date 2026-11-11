import { CHARACTER_STATES } from "@aora-bot/react";
import { describe, expect, it } from "vitest";
import { emotions, phases, type Emotion } from "../../features/robot/model";
import { mapExpression } from "./mapExpression";

describe("Aora expression adapter", () => {
  it("uses only real states exported by the installed Aora package", () => {
    for (const phase of phases)
      for (const emotion of emotions)
        expect(CHARACTER_STATES).toContain(mapExpression(phase, emotion));
  });
  it("prioritizes errors and busy states, while keeping emotion during mock speech", () => {
    expect(mapExpression("error", "happy")).toBe("confused");
    expect(mapExpression("thinking", "sad")).toBe("thinking");
    expect(mapExpression("listening", "angry")).toBe("listening");
    expect(mapExpression("speaking", "neutral")).toBe("humming");
    expect(mapExpression("speaking", "happy")).toBe("happy");
    expect(mapExpression("idle", "surprised")).toBe("surprised");
    expect(mapExpression("idle", "not-an-emotion" as Emotion)).toBe("idle");
  });
});
