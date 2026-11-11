import type { CharacterState } from "@aora-bot/react";
import type { Emotion, Phase } from "../../features/robot/model";

const emotionStates = {
  neutral: "idle",
  happy: "happy",
  sad: "sad",
  curious: "curious",
  surprised: "surprised",
  angry: "angry",
  concerned: "confused",
} satisfies Record<Emotion, CharacterState>;

/** The only boundary translating domain state into Aora's 0.2.0 API. */
export function mapExpression(phase: Phase, emotion: Emotion): CharacterState {
  if (phase === "error") return "confused";
  if (phase === "thinking") return "thinking";
  if (phase === "listening") return "listening";
  // No native speaking state or lip sync: retain an emotional face, or hum.
  if (phase === "speaking" && emotion === "neutral") return "humming";
  return emotionStates[emotion] ?? "idle";
}
