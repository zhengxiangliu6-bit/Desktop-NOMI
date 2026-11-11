import { describe, expect, it } from "vitest";
import snapshot from "../../../contracts/chat-v0.json";
import {
  emotions,
  motions,
  providers,
  MAX_INPUT_CHARS,
  MAX_REPLY_CHARS,
} from "./contract";
describe("implemented backend contract parity", () => {
  it("matches Pydantic enums, required fields and length limits", () => {
    expect(emotions).toEqual(snapshot.response.$defs.Emotion.enum);
    expect(motions).toEqual(snapshot.response.$defs.Motion.enum);
    expect(providers).toEqual(snapshot.response.properties.provider.enum);
    expect(MAX_INPUT_CHARS).toBe(snapshot.request.properties.text.maxLength);
    expect(MAX_REPLY_CHARS).toBe(snapshot.response.properties.reply.maxLength);
    expect(Object.keys(snapshot.request.properties)).toEqual([
      "text",
      "session_id",
    ]);
    expect(snapshot.response.required).toEqual([
      "reply",
      "emotion",
      "motion",
      "session_id",
      "provider",
    ]);
  });
});
