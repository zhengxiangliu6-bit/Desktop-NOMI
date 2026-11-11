import { readdir } from "node:fs/promises";
import { expect, test } from "@playwright/test";

test("production Pages subpath: assets, Mock chat, refresh and home navigation", async ({
  page,
  request,
  baseURL,
}) => {
  const failures: string[] = [];
  const resources: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("response", (response) => {
    if (response.status() >= 400)
      failures.push(`${response.status()} ${response.url()}`);
    if (["script", "stylesheet"].includes(response.request().resourceType()))
      resources.push(response.url());
  });
  page.on("requestfailed", (request) => failures.push(request.url()));
  page.on("request", (request) => {
    if (!request.url().startsWith(baseURL!))
      failures.push(`Unexpected external or root request: ${request.url()}`);
  });
  await page.goto("./?preview=mock");
  await expect(page.getByText("MOCK 模式")).toBeVisible();
  await expect(page.locator(".aora-mark svg").first()).toBeVisible();
  expect(resources.some((url) => url.endsWith(".js"))).toBe(true);
  expect(resources.some((url) => url.endsWith(".css"))).toBe(true);
  expect(resources.every((url) => url.startsWith(`${baseURL}assets/`))).toBe(
    true,
  );

  // Check all emitted chunks, including lazy Aora theme assets.
  for (const file of await readdir("dist/assets")) {
    const response = await request.get(`${baseURL}assets/${file}`);
    expect(response.status(), file).toBe(200);
  }
  await page.getByRole("textbox").fill("你好");
  await page.getByRole("button", { name: "发送消息" }).click();
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  await expect(page.locator(".aora-mark")).toHaveAttribute(
    "data-state",
    "happy",
  );
  await page.reload();
  await expect(page.locator(".aora-mark svg").first()).toBeVisible();
  await expect(page.locator(".message")).toHaveCount(0);
  await page.getByRole("link", { name: "Desktop NOMI 首页" }).click();
  await expect(page).toHaveURL(baseURL!);
  await expect(page.getByRole("textbox")).toBeVisible();

  // No client-side router exists. Unknown deep links must not be advertised.
  expect((await request.get(`${baseURL}not-a-route`)).status()).toBe(404);
  expect((await request.get(`${baseURL}assets/missing.js`)).status()).toBe(404);
  const redirect = await request.get(baseURL!.slice(0, -1), {
    maxRedirects: 0,
  });
  expect(redirect.status()).toBe(301);
  expect(redirect.headers()["location"]).toBe("/Desktop-NOMI/");
  expect(failures).toEqual([]);
  await page.screenshot({
    path: "test-results/pages-preview.png",
    fullPage: true,
  });
});
