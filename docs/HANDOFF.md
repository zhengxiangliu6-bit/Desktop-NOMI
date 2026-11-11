# 任务交接

更新：2026-11-11（Asia/Shanghai）。当前交付：阶段 1「虚拟机器人前端原型」。后端、真实 AI、STT/TTS、持久化与硬件均未实现。

## 恢复入口与分支

先读 AGENTS、README、ARCHITECTURE、API_CONTRACT、ROADMAP 和本记录。开始时工作区干净，原架构 PR #1 已合并到 main；本任务执行 `git fetch origin main`，从 `9b84521` 创建独立分支 `feat/stage1-virtual-robot`，未修改 main。

按本次明确授权先实现前端 Mock 交互；不表示全栈 V0.1（health / 后端 / Windows）或真实 V0.2/V0.3 已完成。后续只做用户指定阶段，不自动接入模型、录音或后端。

## 修改文件与模块

- `frontend/package.json`、`package-lock.json`、`.nvmrc`、`.npmrc`、`tsconfig.json`、`vite.config.ts`、`playwright.config.ts`、`index.html`：精确版本、严格 TS、Vite / Vitest / Playwright 工程入口。
- `frontend/src/main.tsx`、`app/App.tsx`、`app/styles.css`：React StrictMode、中央圆形角色、响应式柔和界面、Mock 标识及 Aora 署名。
- `features/robot/model.ts`、`useRobotController.ts`：阶段/情绪分离、reducer、同步 ref 锁、操作级 AbortController、取消与卸载清理。
- `features/robot/RobotView.tsx`、`DebugPanel.tsx`、`adapters/expression/mapExpression.ts`：Aora 真实 API 映射、错误降级、可折叠调试和 reduced-motion / 隐藏暂停。
- `features/conversation/ChatPanel.tsx`、`services/mockChat.ts`：输入与预设回复、内存最近 60 条、4000 字输入限制、中文输入法回车保护。
- `src/test/setup.ts`、5 个 `*.test.ts(x)`、`frontend/tests/e2e/robot.spec.ts`：单元/组件/生命周期及实际浏览器验收。
- README、ARCHITECTURE、API_CONTRACT、ROADMAP、AORA_RESEARCH、本交接：同步实现边界、运行命令、Mock 映射及验收；未改变未来 HTTP Emotion 枚举。

上面未带 frontend/src 前缀的 features/adapters/services 路径均相对于 frontend/src。没有创建 backend 或空 tests 目录。

## 关键行为

- `circle` / `cream` / `cute`；Aora 0.2.0 不接受 `shape="dot"`，dot 是角色标识。
- `idle → thinking (900ms) → speaking + 情绪 (2400ms) → idle`。无音频，neutral speaking 映射 humming，其他情绪 speaking 保留对应原生表情。工作态 thinking/listening 与 error 优先。
- listening 仅调试演示；angry 为本地情绪扩展，不扩散到尚未实现的 HTTP 契约。
- 调试预览 2400ms 后恢复，预览期间同样禁止重复发送。`/error` 或调试「模拟错误」产生明确故障，恢复待机后再发送。
- 取消/卸载 abort 本地等待，迟到结果通过操作身份与 mounted 标志丢弃；无网络请求、API Key、localStorage 或数据库。
- npm 精确锁定 React/DOM 19.3.1、Aora 0.2.0、Vite 8.3.8、TypeScript 7.0.2、Vitest 5.1.0 等。依 jsdom 31 要求，Node 基线调整至 22.22.2+（22 系列）/24.15.0+（24 系列）；实际云端为 Node 24.22.1 / npm 11.9.0，未单独运行 Node 22。

## 本次执行命令与结果

均为实际运行；未执行的 Windows 能力不计为通过。

- `git status --short --branch`、阅读规范/架构/交接及 `rg --files`：完成；无已有应用代码或依赖。
- `git fetch origin main`、`git switch -c feat/stage1-virtual-robot origin/main`：成功。
- `npm --cache /tmp/nomi-npm-cache view @aora-bot/react version peerDependencies --json`：latest 仍为 0.2.0，React >=19。
- 根目录 `npm --cache /tmp/nomi-npm-cache install --prefix frontend --save-exact react@19 react-dom@19 @aora-bot/react@0.2.0`，及对应 `--save-dev --save-exact` TypeScript、Vite、Vitest、Testing Library、Playwright 等：成功。版本见 package-lock；缓存用 /tmp，未修改系统权限。
- `cd frontend` 后 `npm --cache /tmp/nomi-npm-cache ci`：成功，最终锁文件重装 104 个包。标准本机命令为 `npm ci`，本云端默认 home 缓存不可写时需加上述 cache 参数。
- `npm run typecheck`：最终通过。最初发现 shape dot 不合法，已修正为 circle。
- `npm test`：**5 个测试文件、21 项测试全部通过**。覆盖状态迁移/映射、预设回复、错误恢复、同 tick 重复提交、取消后迟到回复、卸载清理、预览锁、HTML 安全显示及中文输入法。
- `npm run build`：成功生成 dist；Vite 提示主包约 610.72 kB（gzip 212.99 kB）超过 500 kB，构建并未失败，提示未屏蔽。
- `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e`：**2 项全部通过**。桌面实际 SVG 挂载与 idle 帧变化、Mock 往返、取消、错误恢复、调试；375px 移动视口不横向溢出、键盘发送、reduced-motion 连续 12 帧静止。桌面流程无 pageerror，无外部请求。
- 首次 e2e 桌面项因文本定位同时匹配隐藏调试按钮失败；改为唯一 status role 定位后完整重跑通过。移动项首次亦通过。未降低业务断言。
- `npm run dev`：启动成功，当前实例监听本机 5173。`npm run preview`：生产静态预览启动成功，监听 4173。进程不会随新任务保证恢复，需重新启动。
- 额外 Node + Playwright 生产预览烟测：真实 SVG、Mock happy 回复、无页面异常通过；保存干净桌面/手机截图。生成输出 `frontend/test-results/preview-desktop.png`、`preview-mobile.png`，以及 e2e 的 desktop/mobile.png，均被 Git 忽略。
- 临时 Prettier 格式化前端源码/配置；未增加格式化器项目依赖。
- `gh pr list --repo zhengxiangliu6-bit/Desktop-NOMI --head feat/stage1-virtual-robot --json number,url`：GitHub GraphQL Forbidden，API 访问仍受阻，Git 读取正常。最终推送与创建 PR 结果见下方追加记录。

## 已知问题与验收限制

- 本地规则 Mock，不具备真实理解；语音阶段仅状态展示，无录音或声音。Windows、Safari、Firefox 与真实手机未实测；麦克风/扬声器不在本任务范围。
- Aora 聚合入口产生较大的主包及主题动态块，未来按实际性能需求优化，当前未改动或复制第三方源码。
- Aora License 1.1 需按最终拥有者、组织人数及发行方式确认免费/商业资格；界面和 README 保留署名，项目自身 LICENSE 尚待拥有者选择。
- HTTP 契约仍为未来设计，不可把前端本地类型当作已实现服务端 schema。
- 未更改云环境草稿、未部署或发布环境。PR 受 API 权限/网络影响时不能声称创建成功。

## 启动、手动验收与下一步

本机：`cd frontend` → `npm ci` → `npm run dev`，浏览器访问本机 5173。无环境变量或 Key 前置要求；生产预览用 `npm run build` 后 `npm run preview`。完整手动验收步骤见 README。

建议下一任务先在 Windows 做阶段 1 人工验收，再按用户授权决定是否开始后端骨架；不要自动跳到真实 AI 或语音。创建 PR 需要允许 api.github.com 并具备相应 API 权限，勿在聊天发送 Token。

## 提交与 PR 最终结果

- 自动检查文档相对链接（8 个）、JSON 示例/清单、代码围栏与 `git diff --cached --check`：通过。
- 实现提交：`03b7b09`，`feat: add Aora virtual robot frontend with local mock chat`。
- `git push -u origin feat/stage1-virtual-robot`：成功，分支已推送；main 未修改。
- `gh pr create --repo zhengxiangliu6-bit/Desktop-NOMI --base main --head feat/stage1-virtual-robot --title "feat: 阶段 1 虚拟机器人前端与 Mock 交互" --body-file /tmp/nomi-stage1-pr.md`：失败，`Post https://api.github.com/graphql: Forbidden`，**PR 未创建**。
- 可手动创建：https://github.com/zhengxiangliu6-bit/Desktop-NOMI/compare/main...feat/stage1-virtual-robot?expand=1 。允许 api.github.com 并确认 API 权限后可重试 gh；若临时说明文件不存在，依据本交接重建 PR 说明。
- 本最终记录作为后续文档提交推送同一分支。最新提交见 `git log -1`；未合并或发布。
