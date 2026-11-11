# Desktop-NOMI

面向 Windows 电脑的虚拟桌面 AI 伙伴，灵感来自 NOMI 的陪伴体验；本项目与蔚来无隶属或授权关系。先在浏览器中验证动态表情、自然语言与语音交互，再评估桌面封装及 ESP32-S3 硬件。

## 当前状态

当前为 **V0.0 架构基线**：只有规范与设计，没有可运行应用、聊天界面、AI 请求或语音实现。文档中的接口及目录均为目标设计，不代表已经可用。不要运行尚不存在的启动或测试脚本。

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

开发基线计划 Node.js 22 LTS（至少 22.12）、npm、Python 3.12。V0.1 创建真实清单和锁文件后，才提供经过验证的安装命令。后端密钥不使用 `VITE_` 前缀，不进入浏览器构建。

## 文档与开发阶段

先读 [AGENTS.md](AGENTS.md)，再读 [架构](docs/ARCHITECTURE.md)、[接口契约](docs/API_CONTRACT.md)、[路线图](docs/ROADMAP.md) 和 [交接记录](docs/HANDOFF.md)。Aora 的版本、安装与许可证据见 [依赖调研](docs/AORA_RESEARCH.md)。

V0.0 规范 → V0.1 工程骨架与表情 → V0.2 文字对话 → V0.3 情绪联动 → V0.4 语音 → V0.5 Windows 验收。长期记忆、主动交互和真实硬件属于后续版本。

规划的 `frontend/`、`backend/`、`tests/` 在架构文档中定义；当前不创建占位代码。各阶段验收通过后再进入下一阶段。

## 配置与安全

根目录 `.env.example` 仅是变量契约，复制为 `.env` 后由未来后端显式加载；当前没有加载器。前端未来在 `frontend/.env.local` 单独配置公开的 `VITE_API_BASE_URL`。不要把整个根目录 `.env` 暴露给 Vite。

默认仅本机使用，FastAPI 绑定 `127.0.0.1`，精确限制开发来源，不对局域网开放。真实会话和音频不入 Git。云端检查不能替代 Windows 麦克风、扬声器与浏览器权限的人工验收。

## 第三方与许可

Powered by [Aora Bot](https://github.com/sam70361/aora-bot)。其 npm 包采用 **Aora Bot License 1.1**，并非 MIT；免费资格、署名及商业使用限制见调研文档。项目自身尚未选择许可证，不应推定已获得开源再分发授权。公开发行前确认项目许可、依赖许可、角色使用和 NOMI 相关品牌边界。
