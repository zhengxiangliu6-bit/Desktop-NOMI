import type { Emotion } from "../features/robot/model";
import type { ChatService } from "./chatService";
import { ChatServiceError } from "./chatErrors";
export type { ChatService, ChatReply } from "./chatService";
export const MOCK_DELAY_MS = 900;
export const SPEAKING_MS = 2400;
export const PREVIEW_MS = 2400;

export function delay(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Cancelled", "AbortError"));
      return;
    }
    const abort = () => {
      clearTimeout(timer);
      signal.removeEventListener("abort", abort);
      reject(new DOMException("Cancelled", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", abort);
      resolve();
    }, ms);
    signal.addEventListener("abort", abort, { once: true });
  });
}

/** Deterministic local rules. No network, credentials, speech or persistence. */
const preset = async (
  text: string,
  signal: AbortSignal,
): Promise<{ text: string; emotion: Emotion }> => {
  await delay(MOCK_DELAY_MS, signal);
  if (text.trim() === "/error") throw new ChatServiceError("MOCK_ERROR");
  if (/难过|伤心|累|sad/i.test(text))
    return {
      text: "累的时候，就让自己慢一点吧。我在这里，陪你安静待一会儿。",
      emotion: "sad",
    };
  if (/生气|愤怒|angry/i.test(text))
    return {
      text: "收到你的不开心了。一起停一下，给自己一点喘息的空间。",
      emotion: "angry",
    };
  if (/惊|哇|surprise/i.test(text))
    return {
      text: "哇！听起来有新鲜事发生。快把这个小惊喜分享给我吧。",
      emotion: "surprised",
    };
  if (/为什么|什么|怎么|\?|？/.test(text))
    return {
      text: "这是个有趣的问题！我也很好奇。现在是预设回复，等以后接入模型再一起探索。",
      emotion: "curious",
    };
  if (/开心|喜欢|你好|hello|happy/i.test(text))
    return {
      text: "见到你真开心！今天也一起收集一点小小的快乐吧。",
      emotion: "happy",
    };
  return {
    text: "我收到啦。虽然现在只会说预设的话，但很高兴能在桌面上陪着你。",
    emotion: "neutral",
  };
};

export const mockChat: ChatService = async (text, signal) => ({
  ...(await preset(text, signal)),
  motion: "none",
  provider: "frontend-mock",
});
