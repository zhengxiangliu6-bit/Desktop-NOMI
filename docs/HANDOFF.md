# 任务交接

更新：2026-11-11（Asia/Shanghai）。本次仅为现有阶段 1 添加 GitHub Pages 静态在线预览配置，不继续 AI / 语音，不重新设计界面。

## 基线、分支与当前状态

- 先读 AGENTS、README、ARCHITECTURE、API_CONTRACT、ROADMAP 及本交接；网页启用与验收步骤见 [PREVIEW](PREVIEW.md)。
- 已实际 fetch 远端：main=`40c334b`，提交说明为 Merge pull request #2 from feat/stage1-virtual-robot。`git merge-base --is-ancestor 5ad49f7 origin/main` 返回 0，确认阶段 1 已合并，不依赖旧交接的推断。
- 从最新 origin/main 创建独立分支 `deploy/github-pages-preview`。开始时工作区干净，未直接修改 main。
- 预期公网地址：**https://zhengxiangliu6-bit.github.io/Desktop-NOMI/**。当前 **尚未验证已上线**；GitHub API 与该 Pages 域名均被云代理拒绝连接，无法读取/启用 Pages、读取 Actions 结果或实际公网访问。代理 CONNECT 403 不等于站点返回 404，也不能推断仓库管理员权限缺失。
- 本次不合并 PR、不发布云环境；部署需本 PR 合并后按 PREVIEW 在 GitHub 网页启用 Source=GitHub Actions。

## 修改文件与决策

- `.github/workflows/pages.yml`：main push、相关 PR 与手动运行；锁文件安装、typecheck、test、build、既有浏览器测试与静态 Pages 测试。只有 main 非 PR 运行上传 frontend/dist 并部署，PR 只有只读检查权限；deploy 使用 pages:write / id-token:write。无供应商 secrets，不上传 .env 或后端。
- `frontend/vite.config.ts`：固定 `base: "/Desktop-NOMI/"`，大小写与仓库匹配，开发/生产保持一致。
- `frontend/playwright.config.ts`、`tests/e2e/robot.spec.ts`：既有开发回归入口同步子路径，业务断言保留。
- `frontend/playwright.pages.config.ts`、`scripts/serve-pages.mjs`、`tests/pages/preview.spec.ts`：真实 Chromium 检查生产 dist 子路径、全部构建资源、刷新、首页导航和 Mock 回复。Node 静态服务器仅测试 fixture，不是应用后端，不上传到 Pages；没有 SPA fallback。
- `frontend/package.json`：增加 `test:pages`；`tsconfig.json` 纳入新 Playwright 配置。不新增依赖、不更改锁文件。
- README、ARCHITECTURE、PREVIEW、本 HANDOFF：同步公网地址的预期/实测区别、网页操作、路由与开发地址。`frontend/src/` 完全不变，现有 UI、Mock 行为与 Aora 署名保留。

## 执行命令与真实结果

- `git fetch origin main feat/stage1-virtual-robot`：成功。首次使用 origin/feat/stage1-virtual-robot 做祖先检查因该远端跟踪 ref 未创建而失败；随后用已知阶段 1 最终提交 SHA 5ad49f7 对最新 origin/main 检查，返回 0，确认合并。
- `git switch -c deploy/github-pages-preview origin/main`：成功。
- 读取官方 actions/starter-workflows 的 pages/static.yml：成功；采用 checkout@v4、configure-pages@v5、upload-pages-artifact@v3、deploy-pages@v5 的官方流程，加 setup-node@v4。
- `gh api repos/zhengxiangliu6-bit/Desktop-NOMI/pages`：Forbidden，未得到 Pages 配置。没有尝试提取或输出认证值。
- `curl -I --max-time 20 https://zhengxiangliu6-bit.github.io/Desktop-NOMI/`：代理 CONNECT 403，未建立到站点的连接。**不是公网页面验证通过**。
- `npm --cache /tmp/nomi-npm-cache ci --prefix frontend`：成功安装 104 个包；项目依赖未变化。实际环境 Node 24.22.1 / npm 11.9.0；Actions 将按 .nvmrc 使用 22.22.2，尚未实际运行 Actions。
- `npm run typecheck --prefix frontend`：通过。
- `npm test --prefix frontend`：5 个文件、21 项测试全部通过。
- `npm run build --prefix frontend`：成功，dist/index.html 的 JS/CSS 使用 /Desktop-NOMI/assets/。主 JS 约 611 kB 的已知提示保留，未屏蔽。
- `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:pages`（frontend 中）：1 项通过，覆盖全部生成资源 200、JS/CSS 前缀、Mock 回复、刷新后清空内存、品牌导航和未定义路由/资源 404。本地通过不等于 GitHub Pages 已上线。
- 初次既有 e2e 复用之前任务遗留的 Vite 进程，因 npm ci 后其 optimize-deps 缓存过期，React 资源返回 504。用浏览器日志定位后，仅停止本助手启动的旧 dev/preview 进程。
- `CI=1 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e`：干净启动后 2 项全部通过，未改变业务断言。
- 原尝试 go run actionlint 未执行：系统 /usr/bin/go 为其他程序，不支持 Go 的 run 命令。随后下载 actionlint 1.7.7 官方发行包和校验清单，`sha256sum --check --ignore-missing` 通过，才解包执行；未绕过验证。
- `/tmp/nomi-actionlint/actionlint .github/workflows/pages.yml`：通过。
- 文档相对链接、YAML 结构、必须执行的构建步骤、PR/deploy 权限分离与无 secrets 注入检查：通过。`git diff --check`：通过。
- Git 提交、推送和 PR 结果见下面的最终交付记录。

## 路由与界面验证范围

唯一入口 `/Desktop-NOMI/`，当前无业务路由。查询参数、刷新和相对首页链接在静态生产测试中正常；任意深层路径不是受支持页面，未添加 404 跳转补丁。开发地址改为本机 5173/Desktop-NOMI/，本机 preview 为 4173/Desktop-NOMI/，只供开发测试，不作为公网交付地址。

阶段 1 仍采用 React 19 + TS + Vite、Aora 0.2.0，interaction 与 emotion 分离；Mock 900ms 回复、2400ms 无声 speaking 后恢复 idle，错误可恢复、取消/卸载清理。无模型、网络聊天、录音、语音、数据库或设备控制。Windows / Safari / Firefox / 实体音频尚未验证。

## 下一步（用户仅用 GitHub 网页即可）

1. 将本次部署分支通过 PR 合并 main（若 API 创建受阻，compare 页面可手动创建）。
2. Settings → Actions 确认可用；Settings → Pages → Source 选择 GitHub Actions。
3. Actions → Mock preview on GitHub Pages → Run workflow，选择 main；按要求批准 github-pages environment。
4. build/deploy 成功后从输出地址真实访问，检查 Mock、资源、刷新和首页导航，并记录 Actions run URL、部署 SHA 与浏览器结果。
5. 若本云端需要继续自动创建 PR 或验证，环境网络还需允许 api.github.com 和 zhengxiangliu6-bit.github.io；GitHub API 认证能力需另行验证，Git 读写成功不代表 API 可用。不要在聊天发送 Token。

本阶段仅在线预览；后续功能仍需新授权。Pages 无法启用时须按 GitHub 网页具体报错处理，不要擅自改成有密钥的部署或真实 AI 后端。

## 最终交付记录

- `4f54f4c`：部署配置与说明提交成功。
- `git push -u origin deploy/github-pages-preview`：成功，GitHub 接受包括 workflow 在内的分支文件，未遇到 workflow 推送权限拒绝。文件已在远端分支，但这不代表工作流已在 main 激活或运行。
- `gh pr create --repo zhengxiangliu6-bit/Desktop-NOMI --base main --head deploy/github-pages-preview --title "ci: 为阶段 1 添加 GitHub Pages 在线预览" --body-file /tmp/nomi-pages-pr.md`：失败，`Post https://api.github.com/graphql: Forbidden`；**PR 未创建**。
- 可在网页创建 PR：https://github.com/zhengxiangliu6-bit/Desktop-NOMI/compare/main...deploy/github-pages-preview?expand=1 。分支所有变更已具备审查条件。
- Pages 启用、Actions 执行和公网访问均未获得证据，仍标记为未验证。网页操作与验收清单见 PREVIEW。
- 本补充记录再提交并推送同一分支；最新提交以 `git log -1` 为准。不合并 PR，不发布云环境。
