# 阶段 2B：本机前后端集成

当前 HTTP 契约仍是阶段 2A 的 `/api/v0/chat`，本次没有修改路由或字段。开发可选择前端 Mock 或 HTTP API；**所有生产构建（包括 Pages）强制前端 Mock**。没有部署公网后端，也没有执行真实收费模型验证。

## 两种模式

| 前端配置 | 行为 | 可见标识 |
| --- | --- | --- |
| 默认 / VITE_CHAT_MODE=mock | 原有关键词预设回复，无 HTTP 请求 | MOCK 模式 / NOMI · Mock |
| VITE_CHAT_MODE=api（仅开发） | 经同源 Vite Proxy 调用 FastAPI | 首次回复前 API 模式 · Provider 待确认 |
| API 响应 provider=mock | HTTP 链路真实，内容来自后端 Mock | API · 后端 Mock / NOMI · 后端 Mock |
| API 响应 provider=openai | 后端选择 OpenAI 兼容 Provider，仍须单独验证真实供应商 | API · OpenAI 兼容 / 对应消息标签 |

模式由开发配置决定，重启 Vite 后生效，没有 query/localStorage/页面按钮绕过生产 Mock 的入口。新会话不会切换 Provider；实际 Provider 由后端配置决定。

## 分别启动前后端

终端 1（需要 Python 3.12、uv）：

```bash
cd backend
uv sync --frozen --group dev
uv run --frozen python -m app.cli
```

首次集成验证确保后端 `NOMI_LLM_PROVIDER=mock`。没有根 `.env` 时就是此默认值；若已有本机配置，先确认该模式。后端默认仅 loopback 8000，保持原有 Host/Origin 与 CORS，不是公网服务。

终端 2（需要 Node.js 22.22.2+ 或兼容的 24.15+）：

```bash
cd frontend
npm ci
npm run dev
```

默认即 Mock。如需 API 模式，在 **frontend/.env.local** 中写入以下非敏感配置并重启 Vite：

```dotenv
VITE_CHAT_MODE=api
VITE_API_BASE_URL=/api/v0
VITE_CHAT_TIMEOUT_MS=65000
NOMI_DEV_BACKEND_URL=http://127.0.0.1:8000
```

这些配置的模板为 frontend/.env.example。禁止在该文件、VITE_*、浏览器或 Git 中放入 LLM Key / Model / 供应商 Base URL。后端模型配置只在根 `.env` 或后端进程环境中设置。

本机浏览器入口为 `http://127.0.0.1:5173/Desktop-NOMI/`。浏览器请求同源 `/api/v0/chat`，Vite 只将 `/api` 转给可信 loopback 后端；changeOrigin 仅调整代理目标 Host，保留浏览器 Origin，后端仍使用既有精确来源校验。不删除 Origin，不添加通配 CORS。

本阶段 `VITE_API_BASE_URL` 只允许同源 `/api/...` 路径，默认 `/api/v0`；`NOMI_DEV_BACKEND_URL` 为 Vite 服务端配置，只允许 loopback HTTP origin，不进入前端 bundle。默认前端使用 5173，与后端允许的来源一致。若变更前端端口，应显式审核精确来源配置，不要放开所有来源。

这些本机地址是开发/集成测试入口，不是可从其他电脑访问的云端预览。Pages 始终是静态 Mock；只在网页版查看 Pages 不能调用没有公网部署的 FastAPI。

## 会话和错误行为

- 同一页面控制器维护一个活动会话，session_id 仅保存在内存。首轮只发 `{text}`；成功校验回复后保存 ID，续聊附带 session_id。服务对象无全局会话状态，不同页面/控制器彼此隔离。
- 「新会话」显式清空本页聊天和草稿，放弃旧 ID。它会 abort 当前 fetch 并隔离旧回调，但不声称删除或取消了后端会话。新会话首轮仍不带 ID。
- 发送中消息临时显示；成功后成对提交 user/assistant。失败或取消移除临时项，不污染已成功的最近 60 条记录。回到 idle 不删除成功历史；刷新清空本页内存。
- `SESSION_NOT_FOUND` 提醒过期/重启，允许恢复查看旧记录，但必须主动点「新会话」才继续发送。不会静默重建或自动重复请求。
- `SESSION_BUSY`、服务错误、格式错误、配置缺失、网络断开、非 JSON 或前端超时均有固定安全提示。不会展示后端 message、HTML、原始 URL 或上游异常。调试面板显示安全错误码和描述性 motion，不执行任何动作。
- API 模式明确提示真实模型重试可能重复计费。网络失败/非预期响应/客户端超时及主动停止等待都可能是未知提交结果，不能假定后端取消或没计费；可自行等待后手动继续，或主动开始新会话。没有自动重试和幂等承诺。
- 正常状态仍是 idle → thinking → speaking → idle。thinking 为实际在途请求；speaking 是固定 2.4 秒的无声回复展示，不是 TTS。emotion 只经现有 Expression Adapter 映射，motion 仅保存在消息元数据供调试查看。
- 调试阶段/情绪预览及「模拟错误」均为本地行为，即使 API 模式也不发送额外模型请求。

## 验证命令

前端工作目录：

```bash
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run test:e2e
npm run test:pages
npm run test:integration
```

先在 backend 完成 `uv sync --frozen --group dev`，并确保 uv 可用，integration 才能自动启动后端。测试自动启动/停止其服务；集成测试专用端口为前端 5173、后端 8011、静态 Pages fixture 4180，运行前避免被手动服务占用。Linux 已有 Chromium 可设置 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium`；无需关闭 TLS 或改安全边界。

后端工作目录：

```bash
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pytest
```

端到端使用实际 FastAPI 进程、真实 fetch 和同源代理，Provider 为测试 Mock（300ms 延迟、4 秒测试会话 TTL、仅测试模块中的故障场景），不会使用账号。生产 Mock 和业务后端未添加 test:* 特殊指令处理或额外测试路由。

`contracts/chat-v0.json` 是当前 Pydantic 请求/响应的快照。后端 pytest 将其与运行模型比对，前端测试再验证枚举/字段/长度，防止两端漂移。只有实际契约有意修改时，在 backend 运行 `uv run --frozen python scripts/export_contract.py` 并同步消费者；不能单改快照让测试通过。

## 手动验收

1. Mock：不启动后端，默认前端发送「你好」「今天很累」，表情和预设回复仍正常，Network 无 /api 请求。
2. API + 后端 Mock：按上述两个终端启动并配置 api，确认首次标识待确认，回复后标为「后端 Mock」；发送「你好」与「今天很累」，查看两轮相同 session_id，第二轮只有 text/session_id 两字段。
3. 新会话：开始一次在途请求后点「新会话」，新 ID 和新记录不能被旧响应覆盖。停止等待有未知结果提示；motion 不触发 spin、舵机或其他操作。
4. 错误：停掉后端，手动发送，看到安全服务错误；重启后先恢复待机，再发送。旧会话失效时主动新建。服务端超时/格式错误通过自动化 fixture 验收，不需要真实付费调用。
5. Pages：生产构建后运行 test:pages；即便构建环境写着 VITE_CHAT_MODE=api，也必须显示 MOCK 模式且无 API 请求。公网 Pages 本次未验证，不把本地通过当作重新上线证据。

## 阶段 2C 建议（本次未执行）

后续获得明确授权和费用预算后，再在后端安全配置真实供应商。先确认 Chat Completions、max_tokens、可选 JSON mode 与模型兼容性，再做最小一至两轮无隐私输入的实测，记录模式、HTTP 状态与结构校验结果，勿记录 Key 或用户数据。health 只证明配置齐全，不证明账号可用；超时/格式错误回归继续使用 Mock，不以付费重试替代测试。

需要另行验证真实账号权限、计费、TLS/网络、模型结构化输出稳定性和真实上下文 token 限制。当前无公网后端、认证或语音，不因此自动启动部署或硬件工作。
