# 阶段 1 在线预览：GitHub Pages

## 地址与当前状态

预期公网地址：**https://zhengxiangliu6-bit.github.io/Desktop-NOMI/**（仓库名大小写和末尾 `/` 保持一致）。

这是预期地址，不代表已经上线。本次已完成部署配置与本地静态生产验证；当前云环境对 GitHub API 和此 Pages 域名的 CONNECT 请求均返回代理 403，无法读取/开启 Pages 设置、读取 Actions 结果或真实访问公网页面。因此 **GitHub Pages 启用状态、Actions 运行及公网页面均未验证**，不能把本地测试当作已上线证据。

阶段 1 已在远端 main 合并：`40c334b`（PR #2），包含阶段 1 最终提交 `5ad49f7`。本次部署改动在独立分支 `deploy/github-pages-preview`，需要通过 PR 合并后，main 才具有新工作流。

## GitHub 网页操作（无需本机 Node.js）

仓库拥有者可以全部通过网页完成：

1. 打开仓库的 **Settings → Actions → General**。如果 Actions 被禁用，启用 Actions；所用步骤全部为官方 `actions/*`，组织策略也需允许这些步骤。
2. 在 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**，按页面提示保存。不选择 Deploy from a branch，不填写自定义域名。如果缺少设置入口或无编辑权，需要仓库管理员操作；如果网页提示套餐或组织限制，先按提示处理该限制。
3. 打开本次部署分支的 PR，检查文件与自动测试，通过后合并到 main。若助手因 API 限制未创建 PR，可在仓库 **Pull requests → New pull request** 中选择 base `main`、compare `deploy/github-pages-preview`，然后创建。
4. 打开 **Actions → Mock preview on GitHub Pages**。合并涉及前端/工作流的改动会触发；如首次运行因 Pages 尚未启用而失败，完成步骤 2 后选择 **Run workflow → Branch: main → Run workflow**。
5. 等待 build 与 deploy 两个 job 成功。如果 `github-pages` Environment 要求审批，在运行页点击 **Review deployments** 批准。失败时查看对应步骤的日志，不跳过 typecheck、test 或 build。
6. 点击 deploy 输出的 page_url 或 **Settings → Pages → Visit site**。确认地址为上述仓库子路径，按下节做真实公网验收。成功日志加实际浏览器验收完成后，才可记录“已上线”。

创建 PR 的网页入口：https://github.com/zhengxiangliu6-bit/Desktop-NOMI/compare/main...deploy/github-pages-preview?expand=1

Actions 页面：https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions

Pages 设置：https://github.com/zhengxiangliu6-bit/Desktop-NOMI/settings/pages

## 构建部署设计

`.github/workflows/pages.yml`：

- 对 main 的前端/工作流 push、相同范围的 PR，以及手动 workflow_dispatch 运行检查。
- 按 `frontend/.nvmrc` 安装 Node，使用 `npm ci`，依次执行 typecheck、test、build，再执行既有浏览器回归与新增静态 Pages 子路径检查。
- 只有 main 的非 PR 运行上传 `frontend/dist/` 并部署。PR 和手动选择其他分支只验证，不覆盖正式预览。
- build 默认只有 `contents: read`；deploy 单独申请 `pages: write` / `id-token: write`，使用官方 Pages artifact + OIDC 流程。无需添加 PAT 或任何模型 API Key。
- 发布内容只有编译后的公开静态文件，不上传仓库、`.env`、Node 测试服务器、依赖目录或后端。构建没有供应商变量注入；当前源码唯一聊天实现为本地 mockChat。
- 这是共享的 main 预览地址，不是每个 PR 一个临时站点。本次不直接合并 main，不代替用户审批部署环境，也不修改云环境发布配置。

`frontend/vite.config.ts` 固定 `base: "/Desktop-NOMI/"`，生产 JS/CSS、动态 import 和开发入口使用同一仓库前缀。若仓库改名、改成用户主页仓库或启用自定义域名，需要同步调整 base、测试和本文，不能只改访问链接。

## 刷新、路由与资源

当前应用只有单页入口，无 React Router 或业务子路由。`/Desktop-NOMI/`、该地址的查询参数或 hash、刷新、站内相对首页链接均可使用；刷新会清空内存聊天，这是既有行为。

未实现 `/Desktop-NOMI/chat` 等路径，不承诺任意深层链接刷新。没有添加 404.html 重定向或 SPA fallback，也无需为不存在的路由引入路由框架。

新增 `npm run test:pages` 在端口 4180 启动仅用于测试的 Node 静态服务器，以仓库子路径挂载 dist，不提供 SPA fallback。真实浏览器检查所有生成资源为 200、JS/CSS 前缀、Mock 往返、刷新和首页导航，并确认未知路径/资源返回 404。该测试服务器不部署，不是业务后端。

本地复查（可选，使用网页版查看不需要执行）：

```bash
cd frontend
npm ci
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run test:e2e
npm run test:pages
```

云端已有 Chromium 时，最后两条可添加 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium`。开发路径也已同步为本机 `http://127.0.0.1:5173/Desktop-NOMI/`，生产本机 preview 为 `http://127.0.0.1:4173/Desktop-NOMI/`；这些只用于开发测试，不是公网交付地址。

## 公网人工验收清单

- 从公网地址打开，页面标题、Mock 标识、机器人 SVG 与 Aora 署名正常；桌面与手机宽度正常。
- 浏览器开发者工具 Network：入口、JS、CSS 与动态资源没有 404；路径包含 `/Desktop-NOMI/`，没有请求 localhost 或模型/后端 API。
- 发送「你好」，看到 thinking → happy 无声回复 → idle；模拟错误后可恢复；调试面板及停止操作正常。
- 刷新同一入口及带查询参数的入口，页面仍正常；点击品牌首页链接仍在仓库路径下。
- 记录 Actions run URL、部署 SHA、时间、实际访问地址和浏览器结果到 HANDOFF。公网验证失败时记录真实 HTTP/控制台错误，不以预期地址代替结果。

原型仍只有 Mock，没有 AI、录音、语音或硬件，原有 Aora 署名保留。公开发布仍须按 Aora License 1.1 确认最终使用者资格；相关限制见 AORA_RESEARCH。现有主包超过 500 kB 的构建提示未屏蔽，不影响当前静态构建通过。
