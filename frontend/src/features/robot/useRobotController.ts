import { useEffect, useReducer, useRef } from "react";
import { initialState, robotReducer, type Emotion, type Phase } from "./model";
import {
  delay,
  mockChat,
  PREVIEW_MS,
  SPEAKING_MS,
  type ChatService,
} from "../../services/mockChat";

export function useRobotController(service: ChatService = mockChat) {
  const [state, dispatch] = useReducer(robotReducer, initialState);
  const operation = useRef<AbortController | null>(null);
  const mounted = useRef(false);
  const sequence = useRef(0);
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
    operation.current?.abort();
    operation.current = null;
    phase.current = "idle";
    dispatch({ type: "settle" });
  };
  const send = (raw: string): boolean => {
    const text = raw.trim();
    if (
      !mounted.current ||
      operation.current ||
      phase.current !== "idle" ||
      !text ||
      [...text].length > 4000
    )
      return false;
    const job = new AbortController();
    operation.current = job;
    phase.current = "thinking";
    dispatch({
      type: "send",
      message: { id: ++sequence.current, role: "user", text },
    });
    void (async () => {
      try {
        const reply = await service(text, job.signal);
        if (!current(job)) return;
        phase.current = "speaking";
        dispatch({
          type: "reply",
          message: {
            id: ++sequence.current,
            role: "assistant",
            text: reply.text,
          },
          emotion: reply.emotion,
        });
        await delay(SPEAKING_MS, job.signal);
        if (current(job)) cancel();
      } catch (error) {
        if (!current(job)) return;
        operation.current = null;
        phase.current = "error";
        dispatch({
          type: "fail",
          message:
            error instanceof Error
              ? error.message
              : "模拟服务暂时出错，请恢复待机后重试。",
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
    busy:
      state.previewing || (state.phase !== "idle" && state.phase !== "error"),
    send,
    cancel,
    preview,
  };
}
