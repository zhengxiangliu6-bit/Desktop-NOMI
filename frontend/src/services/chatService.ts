import type { Emotion, Motion, Provider } from "../api/contract";
export type ChatMode = "mock" | "api";
export type ReplyProvider = Provider | "frontend-mock";
export interface ChatReply {
  text: string;
  emotion: Emotion;
  motion: Motion;
  provider: ReplyProvider;
  sessionId?: string;
}
/** Session belongs to each controller, never to a shared service singleton. */
export type ChatService = (
  text: string,
  signal: AbortSignal,
  sessionId?: string,
) => Promise<ChatReply>;
