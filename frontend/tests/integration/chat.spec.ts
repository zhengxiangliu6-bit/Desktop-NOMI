import { expect, test } from "@playwright/test";

const send = async (page: import("@playwright/test").Page, text: string) => {
  await page.getByRole("textbox").fill(text);
  await page.getByRole("button", { name: "发送消息" }).click();
};
test("React -> Vite proxy -> actual FastAPI Mock Provider, state and session continuity", async ({
  page,
}) => {
  const payloads: Record<string, unknown>[] = [];
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (r.url().endsWith("/api/v0/chat")) payloads.push(r.postDataJSON());
  });
  await page.goto("./");
  await expect(page.getByText("API 模式 · Provider 待确认")).toBeVisible();
  await send(page, "你好");
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "thinking",
  );
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "happy",
  );
  await expect(
    page.getByText("API · 后端 Mock", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toContainText("无声演示");
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "idle",
  );
  await send(page, "今天很累");
  await expect(page.locator(".message.assistant")).toHaveCount(2);
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "confused",
  );
  expect(payloads[0]).toEqual({ text: "你好" });
  expect(payloads[1]).toMatchObject({
    text: "今天很累",
    session_id: expect.any(String),
  });
  const sessionId = payloads[1]!.session_id;
  await page.getByRole("button", { name: "停止等待" }).click();
  await send(page, "test:timeout");
  await expect(page.getByRole("alert")).toContainText("超时");
  await expect(page.locator(".message.assistant")).toHaveCount(2);
  expect(payloads[2]!.session_id).toBe(sessionId);
  await page.getByRole("button", { name: "恢复待机" }).click();
  await send(page, "恢复");
  await expect(page.locator(".message.assistant")).toHaveCount(3);
  expect(errors).toEqual([]);
});

test("expired backend session requires explicit restart; new conversation omits old ID", async ({
  page,
}) => {
  const payloads: Record<string, unknown>[] = [];
  page.on("request", (r) => {
    if (r.url().endsWith("/api/v0/chat")) payloads.push(r.postDataJSON());
  });
  await page.goto("./");
  await send(page, "hello");
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  await page.getByRole("button", { name: "停止等待" }).click();
  // This test uses the real process's documented four-second test TTL.
  await page.waitForTimeout(4200);
  await send(page, "expired");
  await expect(page.getByRole("alert")).toContainText("会话已失效");
  await page.getByRole("button", { name: "恢复待机" }).click();
  await expect(page.getByRole("textbox")).toBeDisabled();
  await page.getByRole("button", { name: "新会话", exact: true }).click();
  await send(page, "fresh");
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  expect(payloads[2]).toEqual({ text: "fresh" });
});

test("new session and cancellation isolate in-flight responses; debug remains local", async ({
  page,
}) => {
  await page.goto("./");
  await send(page, "test:slow");
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "thinking",
  );
  await page.getByRole("button", { name: "新会话", exact: true }).click();
  await send(page, "new session");
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  await expect(page.locator(".chat-history")).not.toContainText("test:slow");
  await page.getByRole("button", { name: "停止等待" }).click();
  await page.getByText("开发调试", { exact: true }).click();
  const requests: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/")) requests.push(r.url());
  });
  await page.getByRole("button", { name: "模拟错误", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("模拟故障");
  expect(requests).toEqual([]);
});

test("local settings pair, protected save/read, explicit Mock test and key clear", async ({
  page,
}) => {
  // Fake credential only; never enable screenshots, traces or network attachments for this flow.
  await page.goto("./");
  await page.getByRole("button", { name: "AI 设置", exact: true }).click();
  await page.getByLabel("终端一次性配对码").fill("fixture-local-pairing-code");
  await page.getByRole("button", { name: "配对本机后端" }).click();
  await expect(page.getByLabel("Model ID")).toBeVisible();
  await page.getByLabel("Model ID").fill("fixture-configured-id");
  await page.getByLabel("Key 操作").selectOption("replace");
  await page.getByLabel("API Key").fill("fictional-browser-fixture-key");
  await page.getByRole("button", { name: "保存配置" }).click();
  await expect(page.getByLabel("API Key")).toHaveValue("");
  await expect(page.getByText(/Key 状态：已配置/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "测试连接（单次）" }),
  ).toBeDisabled();
  await page.getByRole("checkbox", { name: /我明确授权/ }).check();
  await page.getByRole("button", { name: "测试连接（单次）" }).click();
  await expect(page.getByText("Mock 测试通过，没有供应商请求。")).toBeVisible();
  await page.getByLabel("Provider", { exact: true }).selectOption("openai");
  await page
    .getByLabel("Base URL")
    .fill("https://dashscope.aliyuncs.com/compatible-mode/v1");
  await page.getByLabel("Key 操作").selectOption("replace");
  await page.getByLabel("API Key").fill("fictional-browser-fixture-key");
  await page.getByRole("button", { name: "保存配置" }).click();
  await expect(page.getByLabel("API Key")).toHaveValue("");
  await page.getByRole("button", { name: "关闭设置" }).click();
  // The test factory is still Mock; this exercises managed-chat authorization, not a real model.
  await send(page, "authorized configured chat");
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  await page.getByRole("button", { name: "停止等待" }).click();
  await page.getByRole("button", { name: "AI 设置", exact: true }).click();
  await expect(page.getByLabel("API Key")).toHaveValue("");
  await page.getByLabel("Key 操作").selectOption("clear");
  await page.getByRole("button", { name: "保存配置" }).click();
  await expect(page.getByText(/Key 状态：未配置/)).toBeVisible();
  const storage = await page.evaluate(() => [
    localStorage.length,
    sessionStorage.length,
  ]);
  expect(storage).toEqual([0, 0]);
  await page.reload();
  await page.getByRole("button", { name: "AI 设置", exact: true }).click();
  await expect(page.getByLabel("终端一次性配对码")).toBeVisible();
  await expect(page.getByLabel("API Key")).toHaveCount(0);
});
