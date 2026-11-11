import { useEffect, useReducer, useRef } from "react";
import { MAX_INPUT_CHARS } from "../../api/contract";
import { initialState, robotReducer, type Emotion, type Phase } from "./model";
import {
  delay,
  mockChat,
  PREVIEW_MS,
  SPEAKING_MS,
} from "../../services/mockChat";

import type { ChatService, ChatMode } from "../../services/chatService";
import {
  safeChatError,
  UNKNOWN_RESULT_NOTICE,
} from "../../services/chatErrors";

export function useRobotController(
  service: ChatService = mockChat,
  mode: ChatMode = "mock",
) {
  const [state, dispatch] = useReducer(robotReducer, initialState);
  const operation = useRef<AbortController | null>(null);
  const mounted = useRef(false);
  const sequence = useRef(0);
  const sessionId = useRef<string | undefined>(undefined);
  const expired = useRef(false);
  const requesting = useRef(false);
  // A ref lock blocks same-tick submissions before React renders disabled buttons.
  const phase = useRef<Phase>("idle");
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      operation.current?.abort();
      operation.current = null;
    };
  }, []);

  const current = (job: AbortController) =>
    mounted.current && operation.current === job && !job.signal.aborted;
  const cancel = () => {
    const uncertain = mode === "api" && requesting.current;
    operation.current?.abort();
    operation.current = null;
    requesting.current = false;
    phase.current = "idle";
    dispatch({
      type: "settle",
      ...(uncertain
        ? { notice: UNKNOWN_RESULT_NOTICE }
        : expired.current
          ? { notice: "会话已失效，请点击「新会话」后继续。" }
          : {}),
    });
  };
  const newConversation = () => {
    const uncertain = mode === "api" && requesting.current;
    operation.current?.abort();
    operation.current = null;
    requesting.current = false;
    phase.current = "idle";
    sessionId.current = undefined;
    expired.current = false;
    dispatch({
      type: "reset",
      ...(uncertain ? { notice: UNKNOWN_RESULT_NOTICE } : {}),
    });
  };
  const send = (raw: string): boolean => {
    const text = raw.trim();
    if (
      !mounted.current ||
      operation.current ||
      expired.current ||
      phase.current !== "idle" ||
      !text ||
      [...text].length > MAX_INPUT_CHARS
    )
      return false;
    const job = new AbortController();
    operation.current = job;
    requesting.current = true;
    phase.current = "thinking";
    dispatch({
      type: "send",
      message: { id: ++sequence.current, role: "user", text },
    });
    void (async () => {
      try {
        const reply = await service(text, job.signal, sessionId.current);
        if (!current(job)) return;
        requesting.current = false;
        sessionId.current = reply.sessionId;
        phase.current = "speaking";
        dispatch({
          type: "reply",
          message: {
            id: ++sequence.current,
            role: "assistant",
            text: reply.text,
            provider: reply.provider,
            motion: reply.motion,
          },
          emotion: reply.emotion,
          ...(reply.sessionId ? { sessionId: reply.sessionId } : {}),
        });
        await delay(SPEAKING_MS, job.signal);
        if (current(job)) cancel();
      } catch (error) {
        if (!current(job)) return;
        operation.current = null;
        requesting.current = false;
        phase.current = "error";
        const failure = safeChatError(error);
        expired.current = failure.code === "SESSION_NOT_FOUND";
        dispatch({
          type: "fail",
          message: failure.message,
          code: failure.code,
          ...(mode === "api" &&
          ["NETWORK_ERROR", "CLIENT_TIMEOUT", "INVALID_RESPONSE"].includes(
            failure.code,
          )
            ? { notice: UNKNOWN_RESULT_NOTICE }
            : {}),
        });
      }
    })();
    return true;
  };
  const preview = (nextPhase: Exclude<Phase, "error">, emotion: Emotion) => {
    if (!mounted.current || operation.current || phase.current !== "idle")
      return;
    const job = new AbortController();
    operation.current = job;
    phase.current = nextPhase;
    dispatch({ type: "preview", phase: nextPhase, emotion });
    void delay(PREVIEW_MS, job.signal)
      .then(() => {
        if (current(job)) cancel();
      })
      .catch(() => {
        /* aborted previews need no UI error */
      });
  };
  return {
    state,
    newConversation,
    debugError: () => {
      if (operation.current || phase.current !== "idle") return;
      phase.current = "error";
      dispatch({
        type: "fail",
        message: "这是一次模拟故障，可恢复待机。",
        code: "MOCK_ERROR",
      });
    },
    busy:
      state.previewing || (state.phase !== "idle" && state.phase !== "error"),
    send,
    cancel,
    preview,
  };
}
