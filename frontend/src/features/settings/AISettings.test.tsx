import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AISettings from "./AISettings";
import { setLocalAuthorization } from "../../services/localAuthorization";
const root = "https://dashscope.aliyuncs.com/compatible-mode/v1";
const profile = {
  provider: "mock",
  base_url: "",
  model: "",
  key_configured: false,
  max_tokens: 1024,
  token_parameter: "max_tokens",
  json_mode: false,
  storage: "memory-only",
  revision: 0,
  connection: "not_tested",
  allowed_base_urls: [root],
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
afterEach(() => {
  vi.unstubAllGlobals();
  setLocalAuthorization(null);
});
async function paired(fetcher: ReturnType<typeof vi.fn<typeof fetch>>) {
  fetcher
    .mockResolvedValueOnce(json({ token: "fictional-capability" }))
    .mockResolvedValueOnce(json(profile));
  vi.stubGlobal("fetch", fetcher);
  render(<AISettings onClose={() => {}} onSaved={() => {}} />);
  fireEvent.change(screen.getByLabelText("终端一次性配对码"), {
    target: { value: "fictional-code" },
  });
  fireEvent.click(screen.getByRole("button", { name: "配对本机后端" }));
  await screen.findByLabelText("Model ID");
}
describe("local AI settings secret handling", () => {
  it("keeps key only in uncontrolled input and clears it before save finishes", async () => {
    const fetcher = vi.fn<typeof fetch>();
    await paired(fetcher);
    fireEvent.change(screen.getByLabelText("Key 操作"), {
      target: { value: "replace" },
    });
    fireEvent.change(screen.getByLabelText("API Key"), {
      target: { value: "fictional-input-key" },
    });
    let complete!: (r: Response) => void;
    fetcher.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          complete = resolve;
        }),
    );
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));
    expect(screen.getByLabelText("API Key")).toHaveValue("");
    const call = fetcher.mock.calls.at(-1)!;
    expect(JSON.parse(call[1]!.body as string)).toMatchObject({
      key_action: "replace",
      api_key: "fictional-input-key",
    });
    expect(call[1]!.headers).toMatchObject({
      Authorization: "Bearer fictional-capability",
    });
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    await act(async () =>
      complete(json({ ...profile, key_configured: true, revision: 1 })),
    );
    expect(screen.queryByText("fictional-input-key")).not.toBeInTheDocument();
    expect(screen.getByLabelText("API Key")).toHaveValue("");
  });
  it("requires saved configuration and a fresh confirmation for each test", async () => {
    const fetcher = vi.fn<typeof fetch>();
    await paired(fetcher);
    expect(
      screen.getByRole("button", { name: "测试连接（单次）" }),
    ).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Model ID"), {
      target: { value: "configured-model" },
    });
    expect(screen.getByRole("checkbox", { name: /我明确授权/ })).toBeDisabled();
    fetcher.mockResolvedValueOnce(
      json({ ...profile, model: "configured-model", revision: 1 }),
    );
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));
    await waitFor(() =>
      expect(
        screen.getByRole("checkbox", { name: /我明确授权/ }),
      ).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("checkbox", { name: /我明确授权/ }));
    fetcher
      .mockResolvedValueOnce(json({ ok: true }))
      .mockResolvedValueOnce(
        json({ ...profile, revision: 1, connection: "verified" }),
      );
    fireEvent.click(screen.getByRole("button", { name: "测试连接（单次）" }));
    await screen.findByText("Mock 测试通过，没有供应商请求。");
    expect(
      screen.getByRole("button", { name: "测试连接（单次）" }),
    ).toBeDisabled();
    expect(
      fetcher.mock.calls.filter((c) => String(c[0]).endsWith("/test")),
    ).toHaveLength(1);
  });
  it("clears without resending a secret and ignores upstream error details", async () => {
    const fetcher = vi.fn<typeof fetch>();
    await paired(fetcher);
    fireEvent.change(screen.getByLabelText("Key 操作"), {
      target: { value: "clear" },
    });
    fetcher.mockResolvedValueOnce(
      json(
        {
          error: {
            code: "CREDENTIAL_STORAGE_ERROR",
            message: "private-upstream-detail",
          },
        },
        503,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));
    await screen.findByText("系统凭据保存失败，配置未更改。");
    expect(
      JSON.parse(fetcher.mock.calls.at(-1)![1]!.body as string),
    ).not.toHaveProperty("api_key");
    expect(
      screen.queryByText("private-upstream-detail"),
    ).not.toBeInTheDocument();
  });
});
