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
