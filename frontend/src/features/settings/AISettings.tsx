import { useEffect, useRef, useState } from "react";
import {
  getLocalAuthorization,
  setLocalAuthorization,
} from "../../services/localAuthorization";

interface PublicProfile {
  provider: "mock" | "openai";
  base_url: string;
  model: string;
  key_configured: boolean;
  max_tokens: number;
  token_parameter: "max_tokens" | "max_completion_tokens";
  json_mode: boolean;
  storage: string;
  revision: number;
  connection: string;
  allowed_base_urls: string[];
}
const safeMessages: Record<string, string> = {
  SETTINGS_DISABLED: "请在本机终端以 --enable-settings 启动后端。",
  SETTINGS_FORBIDDEN:
    "配对失败或授权已过期。请重新启用本机配置通道获取配对码。",
  VALIDATION_ERROR: "配置格式无效，请检查受支持的入口、模型和 Key 操作。",
  KEY_SCOPE_CHANGED: "更换入口时必须选择替换或清除 Key。",
  CONFIGURATION_BUSY: "有请求正在运行或配置已变化，请稍后刷新配置再试。",
  CREDENTIAL_STORAGE_ERROR: "系统凭据保存失败，配置未更改。",
  CONFIGURATION_MISSING: "模型配置或 Key 不完整。",
  SECURE_TRANSPORT_UNAVAILABLE:
    "当前代理环境不支持安全连接测试，已阻止供应商请求。",
  UPSTREAM_ERROR: "供应商请求失败，请检查后端配置或账号权限。",
  UPSTREAM_TIMEOUT: "供应商超时；结果可能未知，再次测试可能重复计费。",
  UPSTREAM_INVALID_RESPONSE: "供应商回复不符合结构化协议。",
};
function publicOnly(raw: Record<string, unknown>): PublicProfile {
  if (
    (raw.provider !== "mock" && raw.provider !== "openai") ||
    typeof raw.key_configured !== "boolean" ||
    typeof raw.base_url !== "string" ||
    typeof raw.model !== "string" ||
    typeof raw.revision !== "number" ||
    typeof raw.max_tokens !== "number" ||
    typeof raw.json_mode !== "boolean" ||
    (raw.token_parameter !== "max_tokens" &&
      raw.token_parameter !== "max_completion_tokens") ||
    (raw.storage !== "memory-only" &&
      raw.storage !== "windows-credential-manager") ||
    (raw.connection !== "verified" && raw.connection !== "not_tested") ||
    !Array.isArray(raw.allowed_base_urls) ||
    !raw.allowed_base_urls.every((x) => typeof x === "string")
  )
    throw new Error("返回格式不合法。");
  // Pick known public fields only; never retain an unexpected secret field from a server.
  return {
    provider: raw.provider,
    base_url: raw.base_url,
    model: raw.model,
    key_configured: raw.key_configured,
    max_tokens: raw.max_tokens,
    token_parameter: raw.token_parameter,
    json_mode: raw.json_mode,
    revision: raw.revision,
    storage: String(raw.storage),
    connection: String(raw.connection),
    allowed_base_urls: raw.allowed_base_urls as string[],
  };
}
export default function AISettings({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: () => void;
}) {
  const pairInput = useRef<HTMLInputElement>(null);
  const keyInput = useRef<HTMLInputElement>(null);
  const operation = useRef<AbortController | null>(null);
  const lock = useRef(false);
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [action, setAction] = useState<"keep" | "replace" | "clear">("keep");
  const [confirmed, setConfirmed] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(
    "本机终端授权后才可读取或修改配置。不要在公共页面输入 Key。",
  );
  useEffect(
    () => () => {
      operation.current?.abort();
      operation.current = null;
      lock.current = false;
      if (keyInput.current) keyInput.current.value = "";
      if (pairInput.current) pairInput.current.value = "";
    },
    [],
  );
  const request = async (
    path: string,
    method: string,
    body: unknown,
    signal: AbortSignal,
  ) => {
    const response = await fetch(`/api/v0/settings${path}`, {
      method,
      credentials: "omit",
      redirect: "error",
      cache: "no-store",
      signal,
      headers: {
        "Content-Type": "application/json",
        ...(getLocalAuthorization()
          ? { Authorization: `Bearer ${getLocalAuthorization()}` }
          : {}),
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    const result = await response.json();
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
    if (!response.ok)
      throw new Error(
        safeMessages[result?.error?.code] ?? "设置请求失败，未显示上游细节。",
      );
    return result;
  };
  const run = async (work: (signal: AbortSignal) => Promise<void>) => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    const job = new AbortController();
    operation.current = job;
    const timer = setTimeout(() => job.abort(), 65000);
    try {
      await work(job.signal);
    } catch (error) {
      if (operation.current === job)
        setStatus(
          job.signal.aborted
            ? "等待已停止，后端可能仍在处理。请勿自动重复测试。"
            : error instanceof Error &&
                Object.values(safeMessages).includes(error.message)
              ? error.message
              : "服务不可用或返回无效，请检查本机后端。",
        );
    } finally {
      clearTimeout(timer);
      if (operation.current === job) {
        lock.current = false;
        setBusy(false);
        operation.current = null;
      }
    }
  };
  useEffect(() => {
    if (getLocalAuthorization())
      void run(async (signal) => {
        const current = publicOnly(await request("/read", "POST", {}, signal));
        setProfile(current);
        setStatus("当前页面授权有效，Key 仍不可读回。");
      });
    // Capability exists only in this page's JS memory, never in browser storage.
  }, []);
  const edit = (changes: Partial<PublicProfile>) => {
    if (profile) setProfile({ ...profile, ...changes });
    setDirty(true);
    setConfirmed(false);
  };
  const pair = () => {
    const code = pairInput.current?.value ?? "";
    if (pairInput.current) pairInput.current.value = "";
    void run(async (signal) => {
      const result = await request("/pair", "POST", { code }, signal);
      if (typeof result.token !== "string")
        throw new Error("Invalid authorization");
      setLocalAuthorization(result.token);
      setProfile(publicOnly(await request("/read", "POST", {}, signal)));
      setStatus("已配对。只返回 Key 是否配置，永不读回原文。");
    });
  };
  const save = () => {
    if (!profile) return;
    const key = keyInput.current?.value ?? "";
    if (keyInput.current) keyInput.current.value = "";
    setConfirmed(false);
    void run(async (signal) => {
      const {
        provider,
        base_url,
        model,
        max_tokens,
        token_parameter,
        json_mode,
      } = profile;
      const updated = await request(
        "",
        "PUT",
        {
          provider,
          base_url,
          model,
          max_tokens,
          token_parameter,
          json_mode,
          key_action: action,
          ...(action === "replace" ? { api_key: key } : {}),
        },
        signal,
      );
      setProfile(publicOnly(updated));
      setAction("keep");
      setDirty(false);
      onSaved();
      setStatus(
        "配置已保存，新聊天将使用新配置。旧会话已清空；尚未进行连接测试。",
      );
    });
  };
  const test = () => {
    if (!profile || !confirmed || dirty) return;
    setConfirmed(false);
    void run(async (signal) => {
      await request(
        "/test",
        "POST",
        { confirm_paid_request: true, revision: profile.revision },
        signal,
      );
      setProfile(publicOnly(await request("/read", "POST", {}, signal)));
      setStatus(
        profile.provider === "mock"
          ? "Mock 测试通过，没有供应商请求。"
          : "本次单次连接及结构化回复校验通过。",
      );
    });
  };
  return (
    <section className="ai-settings" aria-label="本地 AI 设置">
      <div className="section-heading">
        <h2>本地 AI 设置</h2>
        <button onClick={onClose}>关闭设置</button>
      </div>
      <p>
        只在受信任的本机 API 模式使用。Key 不写浏览器存储；关闭页面会丢弃授权。
      </p>
      <p role="status">{status}</p>
      {!profile ? (
        <div>
          <label>
            终端一次性配对码
            <input ref={pairInput} type="password" autoComplete="off" />
          </label>
          <button disabled={busy} onClick={pair}>
            配对本机后端
          </button>
        </div>
      ) : (
        <fieldset disabled={busy}>
          <label>
            Provider
            <select
              aria-label="Provider"
              value={profile.provider}
              onChange={(e) =>
                edit({ provider: e.target.value as PublicProfile["provider"] })
              }
            >
              <option value="mock">Mock（不调用供应商）</option>
              <option value="openai">OpenAI 兼容（阿里云百炼）</option>
            </select>
          </label>
          <label>
            Base URL
            <input
              value={profile.base_url}
              list="approved-bailian-roots"
              onChange={(e) => edit({ base_url: e.target.value })}
            />
          </label>
          <datalist id="approved-bailian-roots">
            {profile.allowed_base_urls.map((url) => (
              <option value={url} key={url} />
            ))}
          </datalist>
          <label>
            Model ID
            <input
              value={profile.model}
              maxLength={200}
              onChange={(e) => edit({ model: e.target.value })}
            />
          </label>
          <p>
            Key 状态：{profile.key_configured ? "已配置（不可读回）" : "未配置"}{" "}
            · 存储：
            {profile.storage === "memory-only"
              ? "仅后端内存（重启清空）"
              : "Windows 系统凭据管理器"}{" "}
            · 连接：{profile.connection === "verified" ? "已验证" : "未测试"}
          </p>
          <label>
            Key 操作
            <select
              value={action}
              onChange={(e) => {
                setAction(e.target.value as typeof action);
                setDirty(true);
                setConfirmed(false);
                if (keyInput.current) keyInput.current.value = "";
              }}
            >
              <option value="keep">保留当前 Key</option>
              <option value="replace">更新 Key</option>
              <option value="clear">清除 Key</option>
            </select>
          </label>
          <label>
            API Key
            <input
              ref={keyInput}
              type="password"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              disabled={action !== "replace"}
              maxLength={1024}
              onChange={() => {
                setDirty(true);
                setConfirmed(false);
              }}
            />
          </label>
          <details>
            <summary>兼容参数</summary>
            <label>
              输出 token 上限
              <input
                type="number"
                min={64}
                max={8192}
                value={profile.max_tokens}
                onChange={(e) => edit({ max_tokens: Number(e.target.value) })}
              />
            </label>
            <label>
              token 参数
              <select
                value={profile.token_parameter}
                onChange={(e) =>
                  edit({
                    token_parameter: e.target
                      .value as PublicProfile["token_parameter"],
                  })
                }
              >
                <option value="max_tokens">max_tokens</option>
                <option value="max_completion_tokens">
                  max_completion_tokens
                </option>
              </select>
            </label>
            <label>
              <input
                type="checkbox"
                checked={profile.json_mode}
                onChange={(e) => edit({ json_mode: e.target.checked })}
              />
              JSON Object 模式（需模型支持）
            </label>
          </details>
          <button onClick={save}>保存配置</button>
          <p>
            保存/清除本身不调用模型。修改后先保存，再授权单次测试；失败或取消也可能计费。
          </p>
          <label>
            <input
              type="checkbox"
              disabled={dirty}
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            我明确授权本次连接测试，真实 Provider 可能产生费用
          </label>
          <button disabled={!confirmed || dirty} onClick={test}>
            测试连接（单次）
          </button>
        </fieldset>
      )}
    </section>
  );
}
