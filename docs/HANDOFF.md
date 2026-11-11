# 任务交接

更新：2026-11-11（Asia/Shanghai）。当前交付：**阶段 2B，前后端文字对话集成**。默认/生产/Pages 保持纯前端 Mock，显式开发 API 模式通过同源 Vite Proxy 连接 loopback FastAPI。没有语音、长期记忆、硬件或公网后端部署。

## 基线与恢复入口

- 本次实际 `git fetch origin main` 得到 `d589708`（PR #4 合并阶段 2A）。`git merge-base --is-ancestor c940a4d origin/main` 返回 0，确认 2A 已合并；从该 main 创建独立分支 `feat/stage2b-chat-integration`。开始时工作区干净，未修改 main。
- 先读 AGENTS、README、ARCHITECTURE、当前 API_CONTRACT、本交接和 backend/README。完整启动、模式切换、测试与 2C 建议见 [INTEGRATION](INTEGRATION.md)。
- 严格消费实际 `/api/v0/chat`，没有改动 HTTP 请求/回复结构，未采用 docs/design 归档草案中的 sessions/turn_id。

## 实现决策与兼容性

- 统一 ChatService：`(text, AbortSignal, sessionId?) -> {text, emotion, motion, provider, sessionId?}`。HTTP 将后端 reply 转 text；原 Mock 规则保留，标识 frontend-mock。API provider=mock 明确显示后端 Mock，不伪装真实模型。
- frontend/.env.local 仅非敏感配置：VITE_CHAT_MODE=mock/api、同源 VITE_API_BASE_URL=/api/v0、VITE_CHAT_TIMEOUT_MS；NOMI_DEV_BACKEND_URL 仅 Vite 服务端使用，限制为 loopback HTTP。根 .env 仍只供后端模型配置。没有前端 LLM Key。
- Vite 构建期常量以 command=build 强制前端 Mock，所有生产构建如此，不允许 URL/存储/UI 切换到 API。Pages base 仍为 /Desktop-NOMI/，工作流文件未改。
- 后端 app/ 运行代码和 Host/Origin/CORS/绑定限制均未改。Vite proxy 只调整目标 Host，保留浏览器 Origin，默认前端 5173 与后端原有精确允许来源匹配。
- 会话由每个控制器独立持有，服务对象无会话状态。首轮只发 text，当前请求成功并校验后才记录 UUID，续聊携带 ID。新会话 abort、清空本页记录/草稿和 ID；过期响应不能覆盖新会话。
- pendingMessage 独立于成功历史；成功成对追加 user/assistant，最多 60 条；失败/取消移除临时项，保留全部已有成功记录。输入按 Unicode 码点限制，与后端一致。
- 原 ref 锁、取消/卸载清理、工作阶段/情绪分离和 Expression Adapter 保留。真实 HTTP emotion 经唯一映射层；motion 只存为描述字段，在调试中查看，不执行动作。
- 网络错误、客户端超时、非 JSON/格式错误均使用固定安全文案，不显示服务端 message 或异常原文；错误码/状态先校验。SESSION_NOT_FOUND 需要主动新会话；恢复待机不会偷偷复用失效 ID。
- 停止/网络未知结果明确提醒后端未必停止，重试真实模型可能重复计费，不自动重试。调试预览和模拟错误只在本地发生，不调用模型。
- contracts/chat-v0.json 由当前 Pydantic 生成；后端 pytest 校验快照，前端 unit 校验枚举/必需字段/长度一致。不是新增业务协议。

## 执行命令与真实结果

运行环境 Node 24.22.1 / npm 11.9.0、Python 3.12.14 / uv 0.13.5、Linux 系统 Chromium。所有后端模型均为 Mock/MockTransport，无收费模型或真实凭据调用。

- `git fetch origin main`、祖先检查、`git switch -c feat/stage2b-chat-integration origin/main`：成功。
- 阅读现有文档、控制器、Mock 服务和后端当前 schema/边界：完成。前置兼容性为 reply/text、模式与 Provider 不同、会话失效及生产 Mock 保护，未变更后端契约。
- 在 frontend 中 `npm --cache /tmp/nomi-npm-cache ci`：成功安装 104 个包；未新增运行或测试依赖，锁文件不变。
- 在 backend 中 `uv sync --frozen --group dev`：成功，依赖不变。云端 uv 使用可写 UV_CACHE_DIR=/tmp/nomi-uv-cache 和 UV_SYSTEM_CERTS=true，未关闭 TLS。
- `npm run typecheck`：通过。
- `npm test`：**9 个文件，68 项全部通过**。含 Mock 回归、HTTP 成功/非法输出/非 JSON/服务不可用/取消/超时、全部已实现错误映射、连续 session_id、过期恢复、重复发送、新会话/不同控制器隔离、Unicode 输入、安全文本及诚实 Provider 标签。
- `VITE_CHAT_MODE=api npm run build`：成功，验证即使环境选择 api，生产仍强制 Mock。主 JS 约 618.14 kB（gzip 215.91 kB），保留已有 500 kB 提示，未屏蔽。
- `CI=1 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e`：**2 项通过**，原桌面/手机 Mock、Aora SVG/动画、调试和错误恢复回归。
- `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:pages`：**1 项通过**，生产 Mock 标识、无 API 请求、JS/CSS/动态资源、子路径/刷新/首页导航；不能据此宣称公网 Pages 重新上线。
- `UV_CACHE_DIR=/tmp/nomi-uv-cache UV_SYSTEM_CERTS=true PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:integration`：**3 项通过**。自动启动实际 FastAPI 测试进程 + Mock Provider 和 API Vite；验证 POST、thinking→情绪回复→idle、连续 ID、服务端超时/恢复、真实 TTL 过期、主动新会话、取消隔离和本地调试。无浏览器路由拦截伪造后端响应。
- 初次集成测试与前端格式化操作重叠，Vite 热重载影响首项；固定文件后完整重跑 3 项通过，最后又按顺序运行全部前端检查通过。未弱化业务断言。
- 后端 `uv run --frozen pytest -q`：**68 项全部通过，1 warning**（原 67 + Pydantic 契约快照）。warning 为原有 Starlette TestClient/httpx 弃用提示，未屏蔽。
- 后端 `uv run --frozen ruff check .`、`uv run --frozen ruff format --check .`：通过，30 个 Python 文件格式检查通过。
- actionlint 校验新增 integration.yml 与更新 backend.yml：通过。GitHub Actions 实际运行未验证。
- 文档相对链接、JSON 示例、代码围栏与 `git diff --check`：通过。
- `git diff --name-only origin/main -- backend/app .github/workflows/pages.yml`：为空，后端运行安全边界和 Pages 工作流无改动。
- 所有 Playwright 自行启动的测试进程已由 runner 清理；后续任务不要假定服务仍运行。

## 启动与模式测试

两个终端：backend 中 `uv sync --frozen --group dev`、`uv run --frozen python -m app.cli`；frontend 中 `npm ci`、`npm run dev`。初次使用后端 Mock 默认无需 Key；若根 .env 已选择真实 Provider，应先确认测试模式，勿意外调用收费模型。

Mock：不配置 VITE_CHAT_MODE（或设 mock），前端关键词与调试不发 API 请求，无需启动后端。API：frontend/.env.local 按模板设 api，同源 /api/v0 经默认 loopback 8000；重启 Vite。访问运行这些进程的电脑上的 5173/Desktop-NOMI/。云端本机地址不是远程用户可访问的公网预览。

SESSION_NOT_FOUND 时可保留旧成功记录，但必须点击新会话再发送。停止等待或网络异常后结果可能未知，不自动重试；新会话不表示后端已删除/取消旧任务。speaking 始终只是无声展示。

## 已知限制与未执行

- **真实账号、真实模型输出、真实计费、供应商兼容性、真实网络/TLS：未执行。** HTTP 集成使用实际服务与 Mock Provider，不代表已连通真实模型。
- 未部署公网后端，未验证公网页面新版本、远端 Actions、Windows 实机、实体手机、Safari/Firefox、麦克风、扬声器或硬件。
- API 模式仅开发同源代理；所有生产构建都强制 Mock。当前没有可直接通过 Pages 使用真实模型的公网服务。
- 后端仍为内存、单 worker、无认证/幂等、重启清空。字符预算不是精确 token 数；真实请求重试可能重复计费。
- 前端只提供一个活动会话，新建会清空本页旧聊天和草稿；不实现会话列表、长期存储或同步旧记录。后端上下文窗口可能比本页展示历史更短。
- 保留主 bundle 体积提示与上游 TestClient 弃用提示，未为本阶段扩展性能/依赖升级工作。

## 阶段 2C 建议

见 INTEGRATION 的最小真实验证计划：明确授权/预算后，仅在后端安全配置真实供应商，确认 Chat Completions / max_tokens / JSON mode 支持，再用无隐私输入做一至两轮实测，记录安全结果，不记录 Key/用户数据。health 只代表配置齐全，不代表账号验证通过。不要自动开始公网部署、语音、记忆或硬件。

## 修改文件清单

下方由本次 Git 差异生成，含新增文件；不含被忽略的环境、缓存与测试产物。

```text
.env.example
.github/workflows/backend.yml
.github/workflows/integration.yml
README.md
backend/README.md
backend/scripts/export_contract.py
backend/tests/integration_server.py
backend/tests/test_contract_snapshot.py
contracts/chat-v0.json
docs/API_CONTRACT.md
docs/ARCHITECTURE.md
docs/HANDOFF.md
docs/INTEGRATION.md
docs/ROADMAP.md
frontend/.env.example
frontend/package.json
frontend/playwright.config.ts
frontend/playwright.integration.config.ts
frontend/src/api/contract.test.ts
frontend/src/api/contract.ts
frontend/src/app/App.tsx
frontend/src/app/chatConfig.test.ts
frontend/src/app/chatConfig.ts
frontend/src/app/styles.css
frontend/src/env.d.ts
frontend/src/features/conversation/ChatPanel.test.tsx
frontend/src/features/conversation/ChatPanel.tsx
frontend/src/features/robot/DebugPanel.tsx
frontend/src/features/robot/model.test.ts
frontend/src/features/robot/model.ts
frontend/src/features/robot/useRobotController.api.test.tsx
frontend/src/features/robot/useRobotController.test.tsx
frontend/src/features/robot/useRobotController.ts
frontend/src/services/chatErrors.ts
frontend/src/services/chatService.ts
frontend/src/services/httpChat.test.ts
frontend/src/services/httpChat.ts
frontend/src/services/mockChat.ts
frontend/tests/integration/chat.spec.ts
frontend/tsconfig.json
frontend/vite.config.ts
```
