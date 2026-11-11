# 任务交接

更新：2026-11-11（UTC）。当前交付：**阶段 2C，本地 AI 配置中心**。只开发可信本机 API 模式，不部署真实后端，不进行真实收费调用。下方 2B 记录为历史，不代表本期实现状态。

## 当前基线与恢复

- `git fetch origin main` 得到 `e06e8a9`（PR #5）；`git merge-base --is-ancestor f4ba50c origin/main` 返回 0，确认 2B 已合并。从最新 main 创建 `feat/stage2c-local-ai-settings`，不修改 main。
- 已读 AGENTS、README、ARCHITECTURE、API_CONTRACT、INTEGRATION、旧 HANDOFF、backend/README 和当前配置/聊天实现；没有采用 design 归档草案。
- 详细风险、Windows 操作、保存位置、配对失效与供应商限制见 [LOCAL_AI_SETTINGS](LOCAL_AI_SETTINGS.md)。

## 决策与兼容性

- 管理通道需 CLI `--enable-settings` 显式启用。本机终端一次性码五分钟/最多五次，配对换取三十分钟能力 token；只在浏览器模块内存，不写 storage/cookie/URL。刷新后需重启授权通道重新配对；关闭面板仍可聊天。
- 管理操作叠加 loopback peer、合法 Host、精确本机 Origin、唯一头、同源 Fetch Metadata 与 bearer 校验，不只依赖 CORS。读取采用 POST `/api/v0/settings/read`，因为浏览器同源 GET 不保证 Origin；没有为通过测试放松来源限制。
- 原聊天结构不变，受管真实 Provider 的聊天新增能力授权；旧环境注入路径仍兼容原本机信任模型。设置默认关闭，普通 Mock 不受影响。
- Windows 用 Credential Manager 保存完整受保护记录，无明文落盘或降级；非 Windows 仅内存，外部 Secrets 继续由平台管理。保存先写存储、成功后热切换，失败回滚；忙碌拒绝更改，切换清空旧模型会话。
- 密钥为非受控密码输入，不进入 React state/浏览器存储/URL/日志；提交立即清空，读取只回 key_configured。后台 SecretStr、固定安全错误；供应商回显当前 Key 时拒绝该输出。不能抵御同用户恶意进程/扩展/主动 HAR 采集，不保证 JS/Python 内存零化。
- 配置中心只允许三条精确百炼 HTTPS 根；拒绝地址变体/私网 DNS，连接固定已验证数字 IP并保留 TLS 主机校验，不重定向/重试。新增 anyio/httpcore 直接依赖（原已为传递依赖），不引入账号系统或新框架。
- 系统/环境代理存在时受管安全直连失败关闭，不绕过代理。当前云环境不能做此路径的真实验证。需要代理的企业环境尚待专项支持。
- 保存/读取/清除不调用供应商。连接测试需当前 revision 与 JSON true 明确确认、一次一请求、无自动重试，输出 token 上限 256，返回不含模型文本。max_tokens/max_completion_tokens 可选，JSON Object 按模型显式启用，无固定模型名。
- Pages 工作流不改；所有生产构建继续强制 Mock，并通过编译期分支剔除设置模块。未实现语音、长期记忆、硬件或公网服务。

## 执行命令与结果

依赖安装与检查使用 `npm ci`（frontend）、`uv sync --frozen --group dev`（backend）；uv 使用云端系统 CA 和 /tmp 缓存，不输出凭据。

- backend：`uv run --frozen ruff check .`、`uv run --frozen ruff format --check .` 通过，37 文件；`uv run --frozen pytest -q`：96 passed，1 条现有 Starlette/httpx 弃用警告。`uv lock --check --offline` 通过。
- frontend：`npm run typecheck` 通过；`npm test`：72 passed；`npm run build` 通过，保留既有 Aora 主包超过 500kB 提示。
- `npm run test:e2e`：2 passed；`npm run test:pages`：1 passed；`npm run test:integration`：4 passed（实际 FastAPI 进程 + 测试 Mock Provider，无真实模型）。Pages 测试同时检查无设置控件和生成 JS 不含配置入口/付费测试字段。
- 浏览器命令使用 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium`；本轮最初未设置时因 Playwright 缓存浏览器不存在而启动失败，指定已安装系统 Chromium 后重新执行通过，不是跳过测试。
- 文档相对链接、代码围栏、JSON 与 `git diff --check` 检查通过。没有变更 Pages 工作流，没有执行远端部署/CI。

## 修改文件范围

- 后端：新增 app/settings 的模型、授权管理、路由、Windows/内存 vault、公网 DNS 固定 transport；调整 main、CLI、HTTP 边界、health、Provider/token 参数、pyproject/uv.lock。新增安全配置测试，更新 Provider/集成测试与 fixture。
- 前端：新增 AISettings 与测试、内存授权模块、跨平台 dev:api 启动器；调整 App 入口/样式、HTTP 授权、安全错误、单测和 Playwright 集成/Pages 检查。机器人表情与 Mock 服务不重新设计。
- 文档：README、backend/README、API_CONTRACT、ARCHITECTURE、INTEGRATION、ROADMAP、HANDOFF、LOCAL_AI_SETTINGS；根 .env.example 仅增加非敏感 token 参数。

## 本机启动与下一步

两个终端：backend 中 `uv run --frozen python -m app.cli --enable-settings`；frontend 中 `npm run dev:api`。在本机打开 `http://127.0.0.1:5173/Desktop-NOMI/` → AI 设置 → 终端配对 → 选择地域入口、自己的模型 ID、密码框输入 Key → 保存。然后明确勾选单次测试费用确认，再点击测试连接。不要把真实 Key 发给助手或提交到 Git。

未执行：Windows 原生凭据实机验证、真实百炼账号/模型/TLS/费用、实际供应商参数支持。Windows 使用 API 替身测试，不能声称原生通过。官方兼容文档访问被代理 403 拒绝，不能声称在线文档/入口实连已核实。真实 Key 的所有验证需拥有者本机显式单次授权，先确认地域、模型支持与预算。

已知限制：配对刷新需要重新启用通道；非 Windows 重启丢失配置；企业代理不支持受管直连；仍为单 worker 内存会话。下一步先做 Windows 原生保存/重启/清除验收，再由用户明确点击授权一次百炼连接测试，不自动扩展范围。

## Git 交付

- 实现提交 `c802a41`：`feat: add secure local AI configuration center`；已成功推送 `origin/feat/stage2c-local-ai-settings`。
- `gh pr create --repo zhengxiangliu6-bit/Desktop-NOMI --base main --head feat/stage2c-local-ai-settings --title "feat: 阶段 2C 安全本地 AI 配置中心" --body-file /tmp/nomi-stage2c-pr.md` 失败：`Post "https://api.github.com/graphql": Forbidden`。未创建 PR，不声称远端 CI 已运行。
- 用户可在 GitHub 网页创建 PR：https://github.com/zhengxiangliu6-bit/Desktop-NOMI/compare/main...feat/stage2c-local-ai-settings?expand=1 。描述可依据本交接及 LOCAL_AI_SETTINGS 重建。
- 本交付记录另作文档提交推送同一分支。没有合并、发布或收费模型调用。

---

# 历史：阶段 2B 交接（仅供追溯）

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

## 最终交付记录

- 实现提交 `58e7d40`：`feat: integrate frontend chat with local FastAPI service`。
- `git push -u origin feat/stage2b-chat-integration`：成功，main 未修改。
- `gh pr create --repo zhengxiangliu6-bit/Desktop-NOMI --base main --head feat/stage2b-chat-integration --title "feat: 阶段 2B 前后端文字对话与情绪集成" --body-file /tmp/nomi-stage2b-pr.md`：失败，`Post https://api.github.com/graphql: Forbidden`；本助手未能创建 PR，不声称远端 CI 已执行。
- 准确 compare 入口：https://github.com/zhengxiangliu6-bit/Desktop-NOMI/compare/main...feat/stage2b-chat-integration?expand=1 。API 可访问且授权有效后可重试；临时说明文件丢失时依据本交接重建描述。
- 本记录另作后续文档提交并推送同一分支，最新提交见 `git log -1`。未合并、未发布、未调用真实收费模型。
