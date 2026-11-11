import { expect, test } from "@playwright/test";

test("desktop: real Aora SVG, mock chat, stop, error recovery and preview", async ({
  page,
}) => {
  const errors: string[] = [];
  const externalRequests: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (
      !request.url().startsWith("http://127.0.0.1:5173/") &&
      !request.url().startsWith("ws://127.0.0.1:5173/")
    )
      externalRequests.push(request.url());
  });
  await page.setViewportSize({ width: 1280, height: 1000 });
  await page.goto("/");
  await expect(page.getByText("MOCK 模式")).toBeVisible();
  await expect(page.locator(".aora-mark svg").first()).toBeVisible();
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "idle",
  );
  // Verify the mounted SVG changes over time while idle, not just its container.
  const svg = page.locator(".aora-mark svg").first();
  const firstFrame = await svg.innerHTML();
  await expect.poll(() => svg.innerHTML()).not.toBe(firstFrame);
  await page.getByRole("textbox").fill("你好呀");
  await page.getByRole("button", { name: "发送消息" }).click();
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "thinking",
  );
  await expect(page.getByRole("button", { name: "发送消息" })).toBeDisabled();
  await expect(page.getByRole("status")).toContainText("正在回复 · 无声演示");
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "happy",
  );
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "idle",
    { timeout: 6000 },
  );
  await page.getByRole("textbox").fill("今天很累");
  await page.getByRole("button", { name: "发送消息" }).click();
  await page.getByRole("button", { name: "停止演示" }).click();
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "idle",
  );
  await page.getByText("开发调试", { exact: true }).click();
  await page
    .getByRole("button", { name: "正在倾听 · 演示", exact: true })
    .click();
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "listening",
  );
  await page.getByRole("button", { name: "停止演示" }).click();
  await page.getByRole("button", { name: "模拟错误" }).click();
  await expect(page.getByRole("alert")).toContainText("模拟故障");
  await page.getByRole("button", { name: "恢复待机" }).click();
  await expect(page.getByRole("textbox")).toBeEnabled();
  await page.getByRole("button", { name: "惊讶", exact: true }).click();
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "surprised",
  );
  await page.getByRole("button", { name: "停止演示" }).click();
  await page.screenshot({ path: "test-results/desktop.png", fullPage: true });
  expect(errors).toEqual([]);
  expect(externalRequests).toEqual([]);
});

test("mobile: responsive layout, reduced motion and keyboard access", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator(".aora-mark svg").first()).toBeVisible();
  await expect(page.getByRole("textbox")).toBeVisible();
  await page.getByRole("textbox").fill("哇，惊喜");
  await page.getByRole("textbox").press("Enter");
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "surprised",
  );
  await page.getByRole("button", { name: "停止演示" }).click();
  const distinctFrames = await page.locator(".aora-mark svg").first().evaluate(async (element) => {
    const frames: string[] = [];
    for (let frame = 0; frame < 12; frame++) {
      await new Promise<void>(resolve => requestAnimationFrame(() => resolve()));
      frames.push(element.innerHTML);
    }
    return new Set(frames).size;
  });
  expect(distinctFrames).toBe(1);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expect(
    page.getByRole("link", { name: /Powered by Aora Bot/ }),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/mobile.png", fullPage: true });
});
