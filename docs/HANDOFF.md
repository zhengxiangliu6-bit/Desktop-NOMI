# 任务交接

更新：2026-11-11（Asia/Shanghai）。当前交付：**阶段 2A，独立 FastAPI AI 后端基础**。阶段 1 前端 Mock、Aora 与 Pages 工作流完全未修改；前端集成留到 2B。

## 恢复入口与基线

先读 AGENTS、README、ARCHITECTURE、当前 API_CONTRACT、backend/README 和本记录。旧 V0 全栈接口草案保存到 docs/design/API_V0_PLANNED.md，仅供后续规划；不能当作已实现接口。

本次 `git fetch origin main` 后 main=`7401ce2`，是 Pages 配置 PR #3 的合并提交。工作区开始时干净，从 origin/main 创建独立分支 `feat/stage2a-ai-backend`，没有修改 main。Pages 配置已在 main，但本任务未验证其公网状态，也未触发或改变部署。

## 交付文件

- `backend/pyproject.toml`、`uv.lock`、`.python-version`：Python 3.12、uv 单一锁定机制、FastAPI / Pydantic / Settings / HTTPX / Uvicorn，开发组 pytest / pytest-asyncio / Ruff。
- `backend/app/main.py`、`api/routes.py`、`cli.py`：App factory / lifespan、health 与 chat、运行时 OpenAPI、强制单 worker 的本机 CLI。
- `backend/app/core/`：根 .env + 进程覆盖、脱敏配置/错误、loopback Host / 精确 Origin、64 KiB 流式 body 限制、request_id、无输入/凭据的日志。
- `backend/app/domain/models.py`：Pydantic 请求、回复、健康与错误 schema；emotion / motion 枚举，固定 system 协议。
- `backend/app/adapters/llm/`：Provider Protocol、默认 Mock、可配置 OpenAI 兼容非流式 Chat Completions。没有复制第三方源码或硬编码实际模型/域名/密钥。
- `backend/app/services/conversation.py`：单进程有界内存上下文、会话时效/容量、完整轮次裁剪、并发守卫和失败/取消清理。
- `backend/tests/`：67 项自动化测试及辅助 fixtures，所有真实 Provider 路径都使用 httpx.MockTransport 和虚构凭据。
- `.github/workflows/backend.yml`：新增独立只读后端 CI（锁定安装、Ruff、pytest），不修改 pages.yml。
- `.env.example`、README、backend/README、ARCHITECTURE、API_CONTRACT、ROADMAP、旧契约归档和本交接：实现说明、启动、配置、协议差异与验证限制。

## 当前行为与有意缩小的边界

- 只实现 `GET /api/v0/health`、`POST /api/v0/chat`；运行时 `/docs` 与 `/openapi.json` 可查看 schema。前端不调用这些接口。
- 默认 `NOMI_LLM_PROVIDER=mock`，无 Key 可启动，回复与 provider 字段明确标识 Mock。显式 openai 模式要求 BASE_URL / API_KEY / MODEL 齐全，缺失返回 503，不自动冒充 Mock。
- 结构化模型输出严格为 reply/emotion/motion；非法 JSON、空/超长回复、未知枚举、额外字段、tool/function calls 返回格式错误，不沿用旧草案的 neutral 静默降级。
- 请求/网络错误 `UPSTREAM_ERROR`，超时 `UPSTREAM_TIMEOUT`，模型格式错误 `UPSTREAM_INVALID_RESPONSE`；统一安全错误体与 request_id，失败不污染成功历史，可手动再请求。
- 上下文先用进程内存：100 会话、1800 秒空闲时效、10 轮窗口含本轮、16000 字符总预算，均可配置。仅保存成功的完整 user/assistant 对，容量和字符双重限制。字符预算不是精确 token 数；重启即清空。
- 不实现 SQLite、turn_id/幂等、消息 CRUD、认证、多 worker、语音、主动交互或长期记忆。新 `/chat` 与旧未实现 `/sessions/...` 设计明确区分，2B 应先读当前契约。
- motion 仅 none/nod/tilt/bounce 的提示，没有工具、shell、文件或硬件执行器。输出文本提到操作不会被执行。
- OpenAI Adapter 保留正常 TLS/代理配置，远程地址要求 HTTPS，不允许 URL 内嵌凭据/query/fragment，不跟随重定向、无自动重试、无 tools/functions。json_object 模式可选；真实供应商参数兼容性未验证。

## 执行命令与结果

真实运行环境 Python 3.12.14 / uv 0.13.5；没有向模型服务发出真实请求。

- `git status --short --branch`、`git fetch origin main`、`git log`、`git switch -c feat/stage2a-ai-backend origin/main`：成功。
- 检查配置元数据及所需变量名称的存在性：本机未设置 NOMI_LLM_PROVIDER / BASE_URL / API_KEY / MODEL，环境也无对应 secret 绑定；未打印任何凭据值，不需要为 Mock 测试请求密钥。
- `UV_SYSTEM_CERTS=true UV_CACHE_DIR=/tmp/nomi-uv-cache uv sync --project backend --group dev`：从正常 TLS PyPI 安装成功，生成 portable uv.lock（公开 PyPI / files.pythonhosted.org + SHA256）。仅 backend/.venv 与临时缓存为生成物，被忽略。
- 最初一轮测试有测试源码括号错误，修正后继续；从仓库根执行 pytest 时未加载 backend/pyproject.toml 的 asyncio_mode，导致 36 个异步用例未执行并报失败。改为明确 backend 工作目录后完整重跑，未跳过或削弱断言。后续命令均按下述目录执行。
- 在 `backend/` 中 `uv lock --check --offline`：通过，锁与声明一致。
- 在 `backend/` 中 `uv sync --frozen --group dev`：通过，可复用锁文件安装。
- 在 `backend/` 中 `uv run --frozen ruff check .`：通过；`uv run --frozen ruff format --check .`：通过，27 个 Python 文件已格式化。
- 在 `backend/` 中 `uv run --frozen pytest -q`：**67 passed，1 warning**。覆盖 Mock 正常聊天、请求输入、枚举/格式异常、真实适配器假 HTTP 路径、请求/连接错误、上游和总期限超时恢复、完整轮次/字符预算、容量/时效、并发、取消、会话隔离、流式 body 大小、Host/Origin、脱敏与 CLI 单 worker。
- 上述命令在云端添加 `UV_SYSTEM_CERTS=true UV_CACHE_DIR=/tmp/nomi-uv-cache` 以复用正常系统 CA 和可写缓存；未关闭验证。
- 唯一 pytest warning 为上游 Starlette TestClient 对 httpx 的弃用提示，未屏蔽，当前测试仍真实执行通过；未来升级测试客户端需重跑。
- 本地实进程启动：`NOMI_LLM_PROVIDER=mock uv run --frozen python -m app.cli`。HTTP 烟测验证 health 200、结构化 Mock reply、同 session_id 连续对话、422 错误/request_id 与 OpenAPI ErrorEnvelope schema，均通过；本助手已停止该服务。它不是公网部署，亦不是真实 AI 验证。
- `/tmp/nomi-actionlint/actionlint .github/workflows/backend.yml`：通过。GitHub Actions 尚未在远端运行，不能声称 CI 已通过。
- 文档链接/JSON/TOML/代码围栏、空凭据示例、忽略规则、公开包索引检查：通过。`git diff --check`：通过。
- `git diff --name-only origin/main -- frontend .github/workflows/pages.yml`：为空，确认前端和 Pages 无改动，因此未无意义重复运行未改动的前端测试。

## 未执行与已知限制

- **真实账号凭据、真实供应商/模型回复、真实计费、远端 TLS/API 可达性与跨供应商兼容性：全部未执行。** MockTransport 通过不能代替这些验证，也不能据此声称真实 AI 已连通。
- Windows 实机、前端集成、Pages 到后端连接、麦克风/扬声器、设备均未执行/未实现。
- 本服务无认证，仅本机开发。不得直接公网部署，也不能用放开 CORS 来代替后续身份与网络方案。
- 无持久化、多进程共享或幂等；手动重试真实模型可能重复计费，客户端断线不能保证供应商停止生成。
- 旧全栈目标中 SQLite、完整 session/message 路由与幂等未实现，不将 2A 误记为原 V0.2 全量完成。

## 下一步

阶段 2B 才做前端 API Client、结构化回复/错误映射及明确的连接方案，保留可见的 Mock/真实模式标识。不要自动扩展语音、硬件、真实模型烟测或公网后端。本机启动：`cd backend` → `uv sync --frozen --group dev` → `uv run --frozen python -m app.cli`；详细变量与限制见 backend/README。

提交、推送与 PR 结果在最终交付记录追加。若 API 仍被云代理拒绝，保留远端独立分支并提供 GitHub compare 入口；不能声称 PR 已创建。不要求用户在聊天发送任何 Key。
