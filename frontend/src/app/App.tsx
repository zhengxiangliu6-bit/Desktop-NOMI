import { ChatPanel } from "../features/conversation/ChatPanel";
import { DebugPanel } from "../features/robot/DebugPanel";
import { RobotView } from "../features/robot/RobotView";
import { useRobotController } from "../features/robot/useRobotController";

import { readChatConfig } from "./chatConfig";
import { createHttpChatService } from "../services/httpChat";
import { mockChat } from "../services/mockChat";

const config = __NOMI_PRODUCTION_MOCK__
  ? readChatConfig({}, true)
  : readChatConfig(
      {
        VITE_CHAT_MODE: import.meta.env.VITE_CHAT_MODE,
        VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
        VITE_CHAT_TIMEOUT_MS: import.meta.env.VITE_CHAT_TIMEOUT_MS,
      },
      false,
    );
const service =
  config.mode === "api"
    ? createHttpChatService({
        baseUrl: config.baseUrl,
        timeoutMs: config.timeoutMs,
      })
    : mockChat;

export function App() {
  const { state, busy, send, cancel, preview, newConversation, debugError } =
    useRobotController(service, config.mode);
  return (
    <div className="app-shell">
      <header className="app-header">
        <a className="brand" href="./" aria-label="Desktop NOMI 首页">
          <span className="brand-symbol" aria-hidden="true">
            n<span>•</span>
          </span>
          <span>
            Desktop<span className="brand-light"> / </span>NOMI
          </span>
        </a>
        <span className="mock-badge">
          <span />
          {config.mode === "mock"
            ? "MOCK 模式"
            : state.provider === "mock"
              ? "API · 后端 Mock"
              : state.provider === "openai"
                ? "API · OpenAI 兼容"
                : "API 模式 · Provider 待确认"}
        </span>
      </header>
      <main>
        <div className="intro">
          <p className="eyebrow">A LITTLE COMPANY, A LITTLE JOY</p>
          <h1>
            桌面上的<span>小小陪伴。</span>
          </h1>
          <p>不用说什么大事，今天的心情就很好。</p>
        </div>
        <RobotView phase={state.phase} emotion={state.emotion} />
        {config.mode === "api" && (
          <div className="session-controls">
            <span>HTTP 对话 · 无语音 · 新会话会清空本页记录</span>
            <button onClick={newConversation}>新会话</button>
          </div>
        )}
        {state.notice && (
          <p className="session-notice" role="status">
            {state.notice}
          </p>
        )}
        {state.error && (
          <div className="error-banner" role="alert">
            <p>{state.error}</p>
            <button onClick={cancel}>恢复待机</button>
          </div>
        )}
        <ChatPanel
          key={state.conversation}
          mode={config.mode}
          messages={[
            ...state.messages,
            ...(state.pendingMessage ? [state.pendingMessage] : []),
          ]}
          disabled={busy || state.phase === "error" || state.requiresNewSession}
          busy={busy}
          onSend={send}
          onCancel={cancel}
        />
        <DebugPanel
          state={state}
          disabled={busy || state.phase === "error"}
          onPreview={preview}
          onError={debugError}
        />
      </main>
      <footer>
        <span>
          DESKTOP-NOMI <span className="footer-dot">·</span> FRONTEND PROTOTYPE
          01
        </span>
        <a
          href="https://github.com/sam70361/aora-bot"
          target="_blank"
          rel="noreferrer"
        >
          Powered by Aora Bot ↗
        </a>
      </footer>
    </div>
  );
}
