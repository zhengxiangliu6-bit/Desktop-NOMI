export const phases = [
  "idle",
  "listening",
  "thinking",
  "speaking",
  "error",
] as const;
export type Phase = (typeof phases)[number];
import type { Emotion, Motion } from "../../api/contract";
import type { ReplyProvider } from "../../services/chatService";
export { emotions, type Emotion } from "../../api/contract";

export const phaseLabels: Record<Phase, string> = {
  idle: "自在待机",
  listening: "正在倾听 · 演示",
  thinking: "正在想一想",
  speaking: "正在回复 · 无声演示",
  error: "需要一点帮助",
};
export const emotionLabels: Record<Emotion, string> = {
  neutral: "平静",
  happy: "开心",
  sad: "低落",
  curious: "好奇",
  surprised: "惊讶",
  angry: "生气",
  concerned: "关心",
};
export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  pending?: boolean;
  provider?: ReplyProvider;
  motion?: Motion;
}
export interface RobotState {
  phase: Phase;
  emotion: Emotion;
  messages: ChatMessage[];
  error: string | null;
  previewing: boolean;
  pendingMessage: ChatMessage | null;
  sessionId: string | null;
  provider: ReplyProvider | null;
  errorCode: string | null;
  requiresNewSession: boolean;
  notice: string | null;
  conversation: number;
}
export const initialState: RobotState = {
  phase: "idle",
  emotion: "neutral",
  messages: [],
  error: null,
  previewing: false,
  pendingMessage: null,
  sessionId: null,
  provider: null,
  errorCode: null,
  requiresNewSession: false,
  notice: null,
  conversation: 0,
};
export type RobotAction =
  | { type: "send"; message: ChatMessage }
  | {
      type: "reply";
      message: ChatMessage;
      emotion: Emotion;
      sessionId?: string;
    }
  | { type: "settle"; notice?: string }
  | { type: "reset"; notice?: string }
  | { type: "fail"; message: string; code?: string; notice?: string }
  | { type: "preview"; phase: Exclude<Phase, "error">; emotion: Emotion };

export function robotReducer(
  state: RobotState,
  action: RobotAction,
): RobotState {
  switch (action.type) {
    case "send":
      if (
        state.phase !== "idle" ||
        state.previewing ||
        state.requiresNewSession
      )
        return state;
      return {
        ...state,
        phase: "thinking",
        emotion: "neutral",
        error: null,
        pendingMessage: { ...action.message, pending: true },
        notice: null,
      };
    case "reply":
      if (
        state.phase !== "thinking" ||
        state.previewing ||
        !state.pendingMessage
      )
        return state;
      return {
        ...state,
        phase: "speaking",
        emotion: action.emotion,
        messages: [
          ...state.messages,
          { ...state.pendingMessage, pending: false },
          action.message,
        ].slice(-60),
        pendingMessage: null,
        sessionId: action.sessionId ?? state.sessionId,
        provider: action.message.provider ?? state.provider,
      };
    case "reset":
      return {
        ...initialState,
        conversation: state.conversation + 1,
        notice: action.notice ?? null,
      };
    case "settle":
      return {
        ...state,
        phase: "idle",
        emotion: "neutral",
        error: null,
        errorCode: null,
        previewing: false,
        pendingMessage: null,
        notice: action.notice ?? state.notice,
      };
    case "fail":
      return {
        ...state,
        phase: "error",
        emotion: "concerned",
        notice: action.notice ?? state.notice,
        error: action.message,
        errorCode: action.code ?? null,
        pendingMessage: null,
        requiresNewSession:
          action.code === "SESSION_NOT_FOUND" || state.requiresNewSession,
        previewing: false,
      };
    case "preview":
      if (state.phase !== "idle" || state.previewing) return state;
      return {
        ...state,
        phase: action.phase,
        emotion: action.emotion,
        previewing: true,
      };
  }
}
