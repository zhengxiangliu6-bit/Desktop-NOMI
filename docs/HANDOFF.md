# 任务交接

更新：2026-11-11（Asia/Shanghai）。当前阶段 V0.0 架构基线；尚未实现任何业务功能。

## 恢复入口

先读根 AGENTS.md，再读 README、ARCHITECTURE、API_CONTRACT、ROADMAP 与 AORA_RESEARCH。当前分支 `docs/v0-architecture`，基于初始提交 `2dc5b4af7f83431768b517aa1c1c14e3c345701d`；远端 main 本次检查与该提交一致。无已有用户修改。

## 本次交付与决策

- 改写 README；新增 AGENTS、ARCHITECTURE、ROADMAP、API_CONTRACT、AORA_RESEARCH、本交接、.gitignore、.env.example。
- Windows 浏览器优先，React 19 + TS + Vite / Python 3.12 + FastAPI；尚未引入工程依赖或启动命令。
- 非流式 HTTP、后端可配置 OpenAI 兼容 Adapter、SQLite、本地最小化数据；工作状态与语义情绪分离。
- STT / TTS 默认 disabled，Device 默认 Null；未来阶段再实现。frontend/backend/tests 仅规划，未创建占位代码。
- Aora npm 0.2.0，React >=19，Node >=20；项目计划 Node 22 LTS。自定义 License 1.1，发行前须核实资格与条款。项目自身 LICENSE 待拥有者选择。

## 执行命令与结果

- `git status --short --branch`、`git log -1`、`git ls-remote origin refs/heads/main`：成功，确认初始状态与远端基线。
- `git switch -c docs/v0-architecture`：成功，未修改 main。
- `npm view @aora-bot/react ... --json`：默认缓存路径不可写；改用 `npm --cache /tmp/nomi-npm-cache view ...` 后成功，latest 为 0.2.0。
- `npm view @aora-bot/core version license --json`：404；官方组件依赖实际是 engine，未采用 core。
- `curl` 读取上游 README、React README、LICENSE，以及 `git ls-remote` 上游 HEAD：成功；固定来源见调研文档。
- `npm --cache /tmp/nomi-npm-cache install --prefix /tmp/nomi-aora-research --ignore-scripts --save-exact @aora-bot/react@0.2.0 react@19 react-dom@19`：成功安装 5 个包，仅在临时目录，无项目清单或锁文件改动。
- Node ESM + React DOM server 探针：最初错误预期 SVG，失败；调查确认组件服务端只渲染容器。修正后容器属性、CSS 路径及全部规划映射状态检查通过（React 19.3.1）。未测试客户端动画。
- `gh auth status`：凭据校验失败；`gh api repos/zhengxiangliu6-bit/Desktop-NOMI`：Forbidden。无凭据内容输出。
- 独立 `curl https://api.github.com/...`：CONNECT 403，表明当前代理策略不允许 API 连接；不能仅归因为账户 Token 无效。Git HTTPS 读访问正常，API 权限未获验证。

## 一致性检查

人工核对：各文档阶段边界一致；前后端统一 snake_case 与 `/api/v0`；V0.2 使用 neutral fallback，V0.3 才解析情绪；speaking 映射 humming；语音默认关闭；模型、URL、Key 无默认真实值；前端公开变量不含凭据；取消不保证上游停止；重启 pending 不自动扣费重试。未发现未解决的设计冲突。

自动文档检查、Git 提交、推送和 PR 的最终结果见下方追加记录。应用构建、核心业务测试、Windows、麦克风、扬声器均未运行：当前无应用实现。此任务不改变云环境草稿，不发布环境。

## 下一步

按 ROADMAP 的 V0.1 开始工程骨架与表情验证，不提前实现聊天/AI/语音。先锁定前后端工具版本，再增加真实测试与运行说明。PR 若受阻，需允许当前环境访问 api.github.com 并具备创建 PR 的 GitHub API 权限；不在聊天中发送 Token。

## 最终验证与交付记录

- `python /tmp/check_nomi_docs.py`：通过；9 个必需文件、8 个相对链接、3 个 JSON 示例、代码围栏、配置占位值、7 项忽略规则和无占位业务目录检查通过。检查脚本仅位于临时目录，非业务测试套件。
- `git diff --check`：通过。上述结果只表示文档与配置检查，不代表应用测试通过。
- `git commit -m "docs: establish V0 architecture and development standards"`：成功，初始文档提交 `b44270d`。
- `git push -u origin docs/v0-architecture`：成功，远端分支已存在，main 未修改。
- `gh pr create --repo zhengxiangliu6-bit/Desktop-NOMI --base main --head docs/v0-architecture --title "docs: 建立 Desktop-NOMI V0 架构与开发规范" --body-file /tmp/nomi-pr-body.md`：失败，`Post https://api.github.com/graphql: Forbidden`。PR 未创建；已知 CONNECT 403 仍阻止 API，不能声称已提交 PR。
- 手动创建入口：https://github.com/zhengxiangliu6-bit/Desktop-NOMI/compare/main...docs/v0-architecture?expand=1 。当前工具未提供可调用的浏览器控制能力。允许 API 后可重跑上述 gh 命令；若临时 body 文件已丢失，从本交接与 README 重建说明，勿使用不存在的文件。
- 本交接补充以第二个文档提交保存并推送同一分支；无需发布云环境。最新提交以 `git log -1` 为准。
