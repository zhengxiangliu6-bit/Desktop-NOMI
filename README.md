# Desktop-NOMI

面向 Windows 电脑的虚拟桌面 AI 伙伴，灵感来自 NOMI 的陪伴体验；本项目与蔚来无隶属或授权关系。先在浏览器中验证动态表情、自然语言与语音交互，再评估桌面封装及 ESP32-S3 硬件。

## 当前状态

另行开展 **硬件 H1：ESP32-S3 圆屏表情固件**，独立于前后端，目标仅为 Waveshare ESP32-S3-Touch-LCD-1.85B。代码、构建与调试见 [firmware](firmware/README.md)，板型依据、Windows 整片备份/恢复/烧录和实机待测清单见 [硬件说明](docs/HARDWARE_H1.md)。本阶段没有真实 AI、音频或舵机，实体硬件尚未验证；网页 Mock 与后端安全机制保持原样。

当前为 **阶段 2B：前后端文字对话集成**（阶段 1 外观与 Mock 保留）。`frontend/` 已可运行：中央 Aora 圆形角色、响应式聊天外壳、纯本地 Mock 回复、阶段/情绪独立管理、可折叠调试与错误恢复。界面清晰标识前端 Mock / API / 后端 Mock，尚未执行真实模型验证或实现语音。阶段 2A 提供 FastAPI 服务，阶段 2B 已增加显式开发 API 模式，经同源代理对接结构化回复；默认和所有生产构建仍是前端 Mock。真实账号验证未执行，无持久化或硬件控制。

## 阶段 2A：独立 AI 后端

前端默认和 Pages 保持阶段 1 Mock；阶段 2B 可在开发配置中选择 API。后端默认 Mock，无需 API Key，Python 3.12 + uv：

```bash
cd backend
uv sync --frozen --group dev
uv run --frozen pytest
uv run --frozen python -m app.cli
```

已实现 `GET /api/v0/health` 与 `POST /api/v0/chat`，返回经过 Pydantic 校验的 reply、emotion、motion。Base URL / Key / Model 均由后端环境变量配置。上下文只存在有界单进程内存，重启清空；motion 不执行任何本机或硬件操作。真实供应商账号/兼容性验证 **未执行**。安装、配置、错误和限制见 [后端说明](backend/README.md) 与 [当前接口契约](docs/API_CONTRACT.md)。

## 阶段 2B：前后端文字集成

默认 `npm run dev` 仍为纯 Mock。需要 HTTP 集成时，复制 `frontend/.env.example` 为被忽略的 `frontend/.env.local`，设置 `VITE_CHAT_MODE=api` 并重启 Vite；先在另一终端启动上述后端。默认同源 `/api/v0` 由 Vite 转给 loopback 8000，不放开 CORS，不需要前端密钥。

首轮不带 session_id，成功后续聊复用；「新会话」显式重建，错误不污染成功记录。API 回答标识真实返回的 Provider，后端 Mock 绝不冒充真实模型。取消不能保证后端停止，手动重试真实模型可能重复计费。所有生产构建强制 Mock，无公网后端。

完整的两终端启动、配置、Mock/API 验收、测试和阶段 2C 建议见 [集成说明](docs/INTEGRATION.md)。新增 `npm run test:integration` 使用实际 FastAPI + Mock Provider，无需账号。

## 在线预览（GitHub Pages）

预期地址：**https://zhengxiangliu6-bit.github.io/Desktop-NOMI/**。

已添加 Actions 构建部署配置，但本次云端对 GitHub API 与 Pages 域名均被代理拒绝连接，**尚未验证 Pages 已启用、Actions 已部署或公网页面可用**。部署分支合并并由拥有者启用 Pages 后，即可只通过浏览器查看，不必在 Windows 安装 Node.js。

网页启用步骤、工作流与公网验收见 [在线预览说明](docs/PREVIEW.md)。当前仅发布 Mock 静态前端，无模型 Key、后端或语音。现有界面保持不变。

## 启动与预览

需要 Node.js **22.22.2+（22 系列）或 24.15.0+（24 系列）**，以及 npm；`frontend/.nvmrc` 固定 22.22.2。本次云端实际验证 Node 24.22.1 / npm 11.9.0。无需 `.env` 或 API Key。

```bash
cd frontend
npm ci
npm run dev
```

在运行命令的电脑上，用浏览器访问 `http://127.0.0.1:5173/Desktop-NOMI/`。这不是已部署的公网预览；云端 loopback 地址无法直接从你的 Windows 浏览器访问。可在 Windows 拉取分支后执行相同命令，或查看本次生成的桌面/手机截图。开发服务器默认仅监听本机，不建议直接开放到局域网。

```bash
# 均在 frontend/ 中执行
npm run typecheck
npm test
npm run build
npm run preview
```

生产构建输出 `frontend/dist/`，preview 在本机 `http://127.0.0.1:4173/Desktop-NOMI/` 提供静态预览。以上命令同时适用于 PowerShell，无需 Bash 环境变量写法。

浏览器测试（可选额外安装 Chromium，首次需要网络）：

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

Linux 云端已安装 Chromium 时可执行 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e`；Windows 若使用自有 Chromium，可在 PowerShell 设置 `$env:PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 为其完整路径。测试会自动启动/停止自己的 Vite 服务，截图写入 `frontend/test-results/desktop.png` 与 `mobile.png`（被 Git 忽略）。

## 手动验收

1. 打开页面：确认「MOCK 模式」、大型奶油色圆形角色、自然待机和 Aora 署名；手机宽度无横向溢出。
2. 输入「你好」发送：thinking → 无声 speaking + happy → 2.4 秒后 idle；发送后 0.9 秒得到预设回复。忙碌时不能重复提交，可「停止演示」。Enter 发送，Shift+Enter 换行，中文输入法选词回车不应误发。
3. 输入「今天很累」「哇，惊喜」「为什么？」分别检查 sad、surprised、curious；普通文字返回 neutral。刷新页面清空聊天；只保留本页最近 60 条，不写浏览器存储。
4. 展开「开发调试」，逐个预览交互阶段和情绪，检查 Aora state；listening 不申请麦克风权限，speaking 不播放声音。预览 2.4 秒后自动恢复。
5. 点击「模拟错误」（或发送 `/error`），确认错误提示、发送禁用；点击「恢复待机」后可重新对话。停止一个在途回复后发送新消息，旧结果不能覆盖新状态。
6. 开启系统「减少动态效果」，确认停止持续动画但仍能显示状态和聊天。Windows 实机与实体音频能力未在云端验证。

## 目标与技术栈

| 范围 | 选择 |
| --- | --- |
| 前端 | React 19、TypeScript、Vite；先做 Windows 浏览器应用 |
| 表情 | npm `@aora-bot/react@0.2.0`，通过项目内 Expression Adapter 封装 |
| 后端 | Python 3.12、FastAPI；具体依赖版本在 V0.1 锁定 |
| AI | 后端 OpenAI 兼容 Adapter；模型、Base URL、API Key 均由配置注入 |
| 语音 | 可替换 STT / TTS Adapter；浏览器负责录音和播放 |
| 数据 | 后端 SQLite；配置与密钥不存入对话数据库 |
| 硬件 | 预留 Device Adapter；V0 仅 Null / Mock，不控制真实设备 |
| 测试 | 计划 pytest、Vitest / React Testing Library、Playwright；随对应阶段引入 |

前端使用 npm 和 package-lock 锁定依赖；Node 最低版本由实际测试工具要求调整为上文版本。后端 Python 3.12 工程已建立，使用独立 uv.lock。后端密钥不使用 `VITE_` 前缀，不进入浏览器构建。

## 文档与开发阶段

先读 [AGENTS.md](AGENTS.md)，再读 [架构](docs/ARCHITECTURE.md)、[接口契约](docs/API_CONTRACT.md)、[路线图](docs/ROADMAP.md) 和 [交接记录](docs/HANDOFF.md)。Aora 的版本、安装与许可证据见 [依赖调研](docs/AORA_RESEARCH.md)。

V0.0 规范 → V0.1 工程骨架与表情 → V0.2 文字对话 → V0.3 情绪联动 → V0.4 语音 → V0.5 Windows 验收。长期记忆、主动交互和真实硬件属于后续版本。

阶段 1 按新任务授权先交付前端 Mock 交互，未完成原 V0.1 的 FastAPI/health 及 Windows 验收，亦未实现 V0.2/V0.3 的真实服务。前端测试位于 `frontend/src/**/*.test.*` 与 `frontend/tests/e2e/`；阶段 2A 的后端及 pytest 位于 `backend/`，根 `tests/` 尚未创建；SQLite/幂等仍未交付，2B HTTP 集成已通过 Mock Provider 验证，真实模型验收留到 2C。

## 配置与安全

后端已通过 Pydantic Settings 加载根目录 `.env`，进程环境优先；根 `.env.example` 只有空凭据与非敏感默认值，Mock 无需配置。前端开发配置只在 `frontend/.env.local`，包括公开的模式、同源 API 路径和超时；模型参数及 Key 始终在后端。不要把整个根目录 `.env` 暴露给 Vite。

阶段 2A 后端仅本机使用，FastAPI 绑定 `127.0.0.1`，精确限制开发来源；当前 Pages 在线预览只有静态前端，不包含该后端。真实会话和音频不入 Git。云端检查不能替代 Windows 麦克风、扬声器与浏览器权限的人工验收。

## 第三方与许可

Powered by [Aora Bot](https://github.com/sam70361/aora-bot)。其 npm 包采用 **Aora Bot License 1.1**，并非 MIT；免费资格、署名及商业使用限制见调研文档。项目自身尚未选择许可证，不应推定已获得开源再分发授权。公开发行前确认项目许可、依赖许可、角色使用和 NOMI 相关品牌边界。

## 已知限制

- Mock 依关键词返回固定文本，不具备模型推理、真实记忆或语音能力；演示完成时间固定，不代表语速。
- 浏览器已验证 Linux Chromium 桌面和 375px 手机视口；Windows、Safari、Firefox 及实体手机仍需本机验收。
- 生产构建成功，但主 JS 约 618 kB（gzip 约 216 kB），触发 Vite 的 500 kB 提示；Aora 聚合入口和主题动态块为后续性能优化项，当前不为消除提示改动上游源码。
