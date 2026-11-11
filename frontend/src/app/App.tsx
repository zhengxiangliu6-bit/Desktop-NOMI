import { ChatPanel } from "../features/conversation/ChatPanel";
import { DebugPanel } from "../features/robot/DebugPanel";
import { RobotView } from "../features/robot/RobotView";
import { useRobotController } from "../features/robot/useRobotController";

export function App() {
  const { state, busy, send, cancel, preview } = useRobotController();
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
          MOCK 模式
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
        {state.error && (
          <div className="error-banner" role="alert">
            <p>{state.error}</p>
            <button onClick={cancel}>恢复待机</button>
          </div>
        )}
        <ChatPanel
          messages={state.messages}
          disabled={busy || state.phase === "error"}
          busy={busy}
          onSend={send}
          onCancel={cancel}
        />
        <DebugPanel
          state={state}
          disabled={busy || state.phase === "error"}
          onPreview={preview}
          onError={() => {
            send("/error");
          }}
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
