import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ChatMessage } from "../robot/model";

interface Props {
  messages: ChatMessage[];
  disabled: boolean;
  busy: boolean;
  onSend: (text: string) => boolean;
  onCancel: () => void;
}
export function ChatPanel({
  messages,
  disabled,
  busy,
  onSend,
  onCancel,
}: Props) {
  const [input, setInput] = useState("");
  const history = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (history.current)
      history.current.scrollTop = history.current.scrollHeight;
  }, [messages]);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (onSend(input)) setInput("");
  };
  return (
    <section className="chat-panel" aria-labelledby="chat-title">
      <div className="section-heading">
        <h2 id="chat-title">聊一小会儿</h2>
        <span>仅保留本页最近 60 条</span>
      </div>
      <div
        className="chat-history"
        role="log"
        aria-label="聊天记录"
        aria-live="polite"
        ref={history}
      >
        {messages.length === 0 ? (
          <div className="welcome">
            <span className="mini-spark">✳</span>
            <div>
              <strong>你好，我是 NOMI。</strong>
              <p>给我留句话，让今天多一点陪伴。</p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div className={`message ${message.role}`} key={message.id}>
              <span className="message-author">
                {message.role === "user" ? "你" : "NOMI · Mock"}
              </span>
              <p>{message.text}</p>
            </div>
          ))
        )}
      </div>
      <div className="suggestions" aria-label="试试这些话">
        {["你好呀", "今天有点累", "哇，好惊喜！"].map((text) => (
          <button key={text} disabled={disabled} onClick={() => onSend(text)}>
            {text}
            <span aria-hidden="true"> ↗</span>
          </button>
        ))}
      </div>
      <form onSubmit={submit} className="composer">
        <label className="sr-only" htmlFor="message">
          给 NOMI 留句话
        </label>
        <textarea
          id="message"
          placeholder="今天过得怎么样？"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          maxLength={4000}
          rows={2}
          disabled={disabled}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              e.currentTarget.form?.requestSubmit();
            }
          }}
        />
        <button
          type="submit"
          className="send-button"
          disabled={disabled || !input.trim()}
          aria-label="发送消息"
        >
          <span>发送</span>
          <span aria-hidden="true">↗</span>
        </button>
      </form>
      <div className="composer-note">
        <span>预设回复 · 无 AI / 无语音 · 刷新即清空</span>
        {busy && (
          <button className="text-button" onClick={onCancel}>
            停止演示
          </button>
        )}
      </div>
    </section>
  );
}
