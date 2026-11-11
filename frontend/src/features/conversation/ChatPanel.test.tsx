import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChatPanel } from "./ChatPanel";

describe("chat input", () => {
  it("clears only accepted input, and does not submit during IME composition", () => {
    const onSend = vi.fn().mockReturnValueOnce(false).mockReturnValue(true);
    render(
      <ChatPanel
        messages={[]}
        disabled={false}
        busy={false}
        onSend={onSend}
        onCancel={() => {}}
      />,
    );
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "你好" } });
    fireEvent.click(screen.getByRole("button", { name: "发送消息" }));
    expect(input).toHaveValue("你好");
    fireEvent.keyDown(input, { key: "Enter", isComposing: true });
    expect(onSend).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "发送消息" }));
    expect(input).toHaveValue("");
  });
  it("renders text safely rather than interpreting HTML", () => {
    render(
      <ChatPanel
        messages={[
          { id: 1, role: "user", text: "<img src=x onerror=alert(1)>" },
        ]}
        disabled={true}
        busy={true}
        onSend={vi.fn()}
        onCancel={() => {}}
      />,
    );
    expect(
      screen.getByText("<img src=x onerror=alert(1)>"),
    ).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button", { name: "发送消息" })).toBeDisabled();
  });
});

it("limits input by Unicode code points, including emoji", () => {
  const onSend = vi.fn().mockReturnValue(true);
  render(
    <ChatPanel
      messages={[]}
      disabled={false}
      busy={false}
      onSend={onSend}
      onCancel={() => {}}
    />,
  );
  fireEvent.change(screen.getByRole("textbox"), {
    target: { value: "🙂".repeat(4001) },
  });
  fireEvent.click(screen.getByRole("button", { name: "发送消息" }));
  expect([...(onSend.mock.calls[0]![0] as string)]).toHaveLength(4000);
});

it.each([
  ["mock", "NOMI · 后端 Mock"],
  ["openai", "NOMI · OpenAI 兼容"],
] as const)("labels %s Provider honestly in API mode", (provider, label) => {
  render(
    <ChatPanel
      mode="api"
      messages={[
        {
          id: 1,
          role: "assistant",
          text: "<img src=x>",
          provider,
          motion: "nod",
        },
      ]}
      disabled={false}
      busy={false}
      onSend={() => true}
      onCancel={() => {}}
    />,
  );
  expect(screen.getByText(label)).toBeInTheDocument();
  expect(screen.getByText("<img src=x>")).toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});
