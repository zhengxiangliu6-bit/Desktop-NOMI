export const phases = [
  "idle",
  "listening",
  "thinking",
  "speaking",
  "error",
] as const;
export type Phase = (typeof phases)[number];
export const emotions = [
  "neutral",
  "happy",
  "sad",
  "curious",
  "surprised",
  "angry",
  "concerned",
] as const;
export type Emotion = (typeof emotions)[number];

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
}
export interface RobotState {
  phase: Phase;
  emotion: Emotion;
  messages: ChatMessage[];
  error: string | null;
  previewing: boolean;
}
export const initialState: RobotState = {
  phase: "idle",
  emotion: "neutral",
  messages: [],
  error: null,
  previewing: false,
};
export type RobotAction =
  | { type: "send"; message: ChatMessage }
  | { type: "reply"; message: ChatMessage; emotion: Emotion }
  | { type: "settle" }
  | { type: "fail"; message: string }
  | { type: "preview"; phase: Exclude<Phase, "error">; emotion: Emotion };

export function robotReducer(
  state: RobotState,
  action: RobotAction,
): RobotState {
  switch (action.type) {
    case "send":
      if (state.phase !== "idle" || state.previewing) return state;
      return {
        ...state,
        phase: "thinking",
        emotion: "neutral",
        error: null,
        messages: [...state.messages, action.message].slice(-60),
      };
    case "reply":
      if (state.phase !== "thinking" || state.previewing) return state;
      return {
        ...state,
        phase: "speaking",
        emotion: action.emotion,
        messages: [...state.messages, action.message].slice(-60),
      };
    case "settle":
      return {
        ...state,
        phase: "idle",
        emotion: "neutral",
        error: null,
        previewing: false,
      };
    case "fail":
      return {
        ...state,
        phase: "error",
        emotion: "concerned",
        error: action.message,
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
