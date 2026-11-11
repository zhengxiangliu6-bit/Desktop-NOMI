# Desktop-NOMI 后端：阶段 2A

独立 FastAPI Chat Completions 服务。前端默认和 Pages 保持原本的 Mock；阶段 2B 在显式开发 API 模式中经同源 Vite Proxy 调用本服务。

## 安装、测试与启动

需要 Python 3.12 与 uv（本次使用 uv 0.13.5）。先安装官方 uv，或在已有 Python 环境中 `python -m pip install uv==0.13.5`。以下命令必须在 backend 工作目录执行，以加载其 pytest 配置：

```bash
cd backend
uv sync --frozen --group dev
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pytest
uv run --frozen python -m app.cli
```

默认使用 Mock，无需 `.env`、Key 或网络模型。CLI 仅监听本机 8000，单 worker，关闭访问 URL 日志；本机交互文档位于 `http://localhost:8000/docs`。这是开发服务，不是公网部署或 Pages 后端。

本机测试请求（HTTP 客户端 / Swagger 均可）：

```http
GET /api/v0/health

POST /api/v0/chat
Content-Type: application/json

{"text":"你好"}
```

续聊时带上返回的 session_id。完整 schema、限制和错误码见 [API 契约](../docs/API_CONTRACT.md)。

## 配置

后端以仓库根路径加载 `.env`，再由进程环境覆盖；根 `.env.example` 可以作为非敏感模板。密钥只能放到被忽略的本机 `.env` 或安全环境变量中，不能放入前端、提交到 Git 或写进截图/日志。服务不提供远程设置 API。

| 环境变量 | 默认值 / 说明 |
| --- | --- |
| NOMI_LLM_PROVIDER | mock；显式 openai 才调用模型，失败不自动降级 Mock |
| NOMI_LLM_BASE_URL | 无默认；完整 API 根路径，例如供应商要求的 /v1 也须提供；只追加 /chat/completions |
| NOMI_LLM_API_KEY | 无默认，SecretStr 脱敏；openai 模式必需 |
| NOMI_LLM_MODEL | 无默认，openai 模式必需 |
| NOMI_LLM_TIMEOUT_SECONDS | 60，总期限，范围 (0,120] |
| NOMI_LLM_MAX_OUTPUT_TOKENS | 1024，范围 64..8192；发送 max_tokens |
| NOMI_LLM_JSON_MODE | false；供应商支持时可开启 response_format=json_object，否则仅 system prompt + 严格结果校验 |
| NOMI_CONTEXT_MAX_TURNS | 10，包含本轮；范围 1..50 |
| NOMI_CONTEXT_MAX_CHARS | 16000，system + 文本/历史 JSON 的码点预算；范围 5000..128000 |
| NOMI_MAX_SESSIONS | 100，范围 1..1000 |
| NOMI_SESSION_TTL_SECONDS | 1800，范围 (0,86400]，进程内惰性清理 |
| NOMI_HOST / NOMI_PORT | 127.0.0.1 / 8000，仅允许 loopback Host 与非特权端口 |
| NOMI_ALLOWED_ORIGINS | 逗号分隔精确来源，默认本机 5173；无路径或通配 |

远程 Base URL 要求 HTTPS；仅 loopback 允许 HTTP，用于本地兼容服务。禁止 URL 内嵌账号/密码、query、fragment 和原始空白；不跟随重定向，Key 只发往所配置端点。HTTPX 保留正常 TLS 验证和运行环境的代理/CA 配置，不允许关闭证书验证。

Provider 使用非流式 `/chat/completions`、messages、model、max_tokens；不发送 tools/functions。不是所有供应商或模型都支持相同的参数组合；需要真实账号的兼容性测试本次 **未执行**。更换 Base URL / Model 不需修改源码，但必须由可信管理员配置，不能接受用户聊天覆盖。

## 验证范围与限制

- pytest 全部使用 Mock Provider / httpx.MockTransport / 虚构凭据；模拟适配器路径通过不代表真实账号已通过。
- 错误区分：UPSTREAM_ERROR（请求/网络）、UPSTREAM_TIMEOUT（超时）、UPSTREAM_INVALID_RESPONSE（格式/枚举）；失败不污染上下文，可手动重新请求。
- 当前仅内存上下文，重启清空；不支持多 worker、SQLite、持久化、幂等去重或用户认证。默认只供本机开发，不直接开放公网。
- motion 只是枚举；没有 shell、文件写入、工具执行或硬件控制模块。语音与真实模型烟测未执行；2B HTTP 集成由实际 FastAPI + 测试 Mock 验证，见 [集成说明](../docs/INTEGRATION.md)。
- pytest 当前有一项上游 Starlette TestClient 对 httpx 的弃用提示；未屏蔽，不影响本次已执行用例，但未来升级测试客户端需重新验证。

## 阶段 2C 本地配置

`uv run --frozen python -m app.cli --enable-settings` 显式启用一次性终端配对。Windows 用 Credential Manager 存储完整受保护记录，非 Windows 仅内存，无明文文件回退。正常 Windows CLI 读取已保存配置，但设置和受管真实聊天仍需启用并配对授权。前端 `npm run dev:api` 无需编辑 `.env` 即可进入开发 API 模式。

新增受保护 `/api/v0/settings/pair`、`/read`、PUT settings、`/test`；读状态不返回模型 Key，配对 token 是另一种短期本机能力，只留页面内存。受管真实聊天也需该授权。连接测试须每次显式确认，最多一次 Provider 调用、输出参数至多 256，不自动重试。配置变更清空旧会话，忙碌时拒绝更改。

仅允许精确百炼公开兼容根，连接时检查并固定公网 IP、保留 TLS 主机校验；受管代理环境失败关闭，原有可信环境/Secrets 路径保留。本次无真实模型/Windows 原生验证，完整限制见 [LOCAL_AI_SETTINGS](../docs/LOCAL_AI_SETTINGS.md)。
