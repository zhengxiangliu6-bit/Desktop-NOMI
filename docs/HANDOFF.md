# H1 硬件固件交接

更新：2026-11-13（Asia/Shanghai）。当前新增交付：**独立 ESP32-S3 圆屏表情固件 H1**。实体硬件、Windows 驱动/烧录/恢复未验证；现有阶段 2B 和 Pages Mock 保留，下方历史交接继续有效。

## 基线与调查

- 工作区起始干净，阅读 AGENTS、README、ARCHITECTURE、API_CONTRACT、ROADMAP、HANDOFF 及 Expression Adapter。`git fetch origin main` 后从最新 `e06e8a9` 创建 `feat/h1-esp32-face`，未修改 main。
- 官方仓库固定提交 `5a98b8da1948340c07032a408ac0d93c47ca558f`，阅读 Rev1.1 原理图、README、ESP-IDF LVGL 示例、BSP 头文件/显示实现、Arduino 示例驱动及官方恢复指南。
- 确认 ESP32-S3R8 / 16 MB Flash / 8 MB 八线 PSRAM；ST77916 360×360 QSPI；所有引脚来自该板，未借用其他板配置。官方框架 IDF 5.5.4 / LVGL 9.5.0。细节见 [HARDWARE_H1](HARDWARE_H1.md)。
- 下载并核对官方合并镜像 20261109，10,514,658 字节，SHA256 `10dbcd2655fe44249840ff2b8879ff11152a7d73e1d6a3ebd8311c1f8e2b3b05`；esptool 4.11.0 image_info 识别 ESP32-S3，bootloader checksum/hash 有效。镜像未加入本仓库。
- 官方恢复方式为合并镜像写 0x0（完整重置时先擦除）；自己整片备份则读取/验证 0x0 起 16 MB 后原址写回。两种恢复目的不同，文档已区分，未对设备执行。原理图 Key1 为电源、Key2 为 BOOT，不假设独立 RESET 按钮。

## 设计与范围

- 新增独立 `firmware/` ESP-IDF 5.5.4 工程。依赖仅 LVGL 9.5.0 固定提交 `85aa60d18b3d5e5588d7b247abf90198f07c8a63`，prepare.py 获取/核验，下载目录忽略。不依赖组件注册表、不打包 Web 运行时。
- 显示层提取该板官方初始化表，保留两版面板 ID 选择、GPIO、80 MHz QSPI、RGB565 和首帧后背光；使用官方仓库随附的 Espressif ST77916 C 驱动，不将其冒充注册表 2.0.1。驱动逐字节核对，初始化表清理行尾空白后与上游核对一致。许可/修改见 [NOTICE](../firmware/components/nomi_panel/NOTICE.md)。
- LVGL 固定图元绘制奶油色脸、眼睛、嘴、腮红/活动提示。idle/blink/happy/sad/curious/thinking/listening/speaking 均实现，安全半径 160；没有图片帧、Aora SVG/源码/素材。两个内部 DMA 条带缓冲总计 23,040 字节。
- FaceModel 为独立 C++17 状态机：情绪/阶段正交、5 秒 TTL（内部可设 1..30000 ms）、工作态优先但不延长情绪、180 ms 插值、2.5–6 秒自然眨眼。眨眼覆盖后恢复原状态；非法输入回退 idle；单调 64 bit 时钟。
- 主任务单独拥有状态机与 LVGL，20 ms 更新几何，FreeRTOS 5 ms yield；DMA 用信号量等待且超时 fail-fast，面板初始化保留必要协议延时。USB Serial/JTAG 有界非阻塞读取本地命令，支持 demo/status/idle；不实现远程设备协议。
- 未初始化触摸、音频、传感器、SD、Wi-Fi，也未实现真实 AI、语音、记忆、舵机或 Device Adapter。listening/speaking 为无声动画。
- Windows 先检查准确板型与安全状态、两份 16 MB 备份/哈希/verify_flash、下载校验官方镜像，再用 idf.py flash；不是将 app bin 写到 0x0。完整步骤与验收表见 HARDWARE_H1。

## 验证记录

- `python firmware/scripts/prepare.py`：LVGL 提交核验通过。
- `g++ -std=c++17 -Wall -Wextra -Werror firmware/tests/face_model_test.cpp firmware/main/face_model.cpp -I firmware/main -o /tmp/nomi-face-model-test` 及执行：通过。
- `cmake -S firmware/tests -B /tmp/nomi-render-tests -G Ninja -DNOMI_RENDER_TESTS=ON`、`cmake --build /tmp/nomi-render-tests -j 6`、`ctest --test-dir /tmp/nomi-render-tests --output-on-failure`：**2/2 通过**。一项覆盖核心状态/TTL/插值/非法值/长运行/跨 32 bit 毫秒；一项链接真实 LVGL 渲染八种表情，检查图像非空、连续表情不同、所有前景像素在半径 160 安全圆内，并输出八张 PPM。已查看合成预览；这是离屏渲染，不模拟显示硬件。
- 初次原生构建缺少 cmake，使用临时 Python 环境安装构建工具；首次 renderer 编译发现 C++ 枚举位或需显式转换，已修正后重建通过。最初插值测试误复用非初始状态，改用新模型后通过，没有更改动画状态语义规避测试。
- 官方表/驱动来源核对、Markdown 本地链接检查：通过。
- 官方 IDF v5.5.4 源码提交 `735507283d5b2f9fb363a1901172dbd9e847945d`（子模块完整且干净），官方 tools.json 校验安装 Xtensa GCC `esp-14.2.0_20260121`。Linux Python 3.12.14 / CMake 3.30.5 / Ninja 1.13.2 / esptool 4.11.0。通用 Docker 镜像下载量大，取消下载，改用上述原生工具链构建；没有宣称在容器内运行成功。
- 云端 Python 按 IDF requirements.core.txt 安装，`idf_tools.py check-python-dependencies` 通过；设置 IDF_PYTHON_CHECK_CONSTRAINTS=no，未使用另行下载的供应商 constraints 文件。没有关闭 TLS 或绕过网络策略。用户 Windows 仍按官方 v5.5.4 安装器配置。
- ESP32-S3 `idf.py build`：**成功**，生成 app/bootloader/partition table/ELF/map/flash_args；最终 app bin **538,016 字节**，分区大小 0x177000（约 65% 余量）。`idf.py size` 成功，静态 DIRAM 约 80,423 字节；动态缓冲/实际 PSRAM 与总运行内存须实机日志确认。esptool image_info 检查 app 为 ESP32-S3、checksum/hash 有效。没有运行 flash/erase/monitor 或连接实体设备。
- 首次 IDF 编译发现 Xtensa uint32_t 与主机 unsigned int 类型不同，std::clamp 推导失败；改为显式 std::clamp<uint32_t> 后目标构建成功。最终变更后重新执行目标 build/size、原生 2/2 测试及 AddressSanitizer/UndefinedBehaviorSanitizer 检查，全部通过。初次命令误将 -j 传给 idf.py，未开始编译，随后改用实际支持的 idf.py build。
- IDF 首次配置存在上游 Kconfig 无 0x 前缀的弃用 NOTE，以及提示检测到 LVGL manifest 但组件管理器已禁用；这是固定 GitHub 依赖的预期行为。最终增量编译无 warning/error，未屏蔽编译诊断。
- actionlint 1.7.7 检查新增 firmware.yml：通过。CI 容器固定官方 v5.5.4 amd64 manifest digest；远端工作流尚未在交付记录时确认执行。
- 官方表/驱动来源核对、本次 Markdown 本地链接及 git diff --check：通过。
- 新增独立 firmware.yml：原生状态/渲染测试 + IDF 5.5.4 目标构建，上传编译产物及第三方许可；无烧录/发布/部署步骤。远端 Actions 运行结果另行记录，未执行不算通过。
- 前后端运行代码、.env.example、Pages 工作流差异为空；本阶段未重跑不受影响的 Web/后端测试，没有更改 Key 或生产 Mock 机制。

## 已知限制与下一步

- **没有接入实体板。** 实际 PSRAM、LCD ID/批次、QSPI 时序、颜色/方向、闪烁/撕裂、USB 重枚举、串口响应、Windows 工具链/驱动、备份/烧录/恢复、30 分钟稳定性均未验证。
- 未知面板 ID 使用官方驱动默认表并报警日志；不能将此回退声称为支持新硬件版本。先收集该板 ID/丝印/日志，不套用别的板引脚。
- 软件目标与硬件实测必须分别记录；照 HARDWARE_H1 表逐项验收。任何恢复实际执行都以自己同板未加密备份与已核对官方镜像为依据。
- 触摸未接入，串口可测试全部表情；如需触摸交互、AI/音频/舵机或主机通信，另定后续阶段。

## 修改文件与恢复入口

新增 firmware/（工程/锁定依赖获取脚本/显示驱动与许可/状态机/渲染/主循环/原生测试）、.github/workflows/firmware.yml、docs/HARDWARE_H1.md；更新 README、ARCHITECTURE、ROADMAP、本交接。硬件备份不入库。工程恢复用分支提交，实体恢复用 HARDWARE_H1 两种方案；不要将两者混淆。

## 提交与 PR

待最终验证后记录分支推送、提交与 PR 的真实结果。

---

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

## 最终交付记录

- 实现提交 `58e7d40`：`feat: integrate frontend chat with local FastAPI service`。
- `git push -u origin feat/stage2b-chat-integration`：成功，main 未修改。
- `gh pr create --repo zhengxiangliu6-bit/Desktop-NOMI --base main --head feat/stage2b-chat-integration --title "feat: 阶段 2B 前后端文字对话与情绪集成" --body-file /tmp/nomi-stage2b-pr.md`：失败，`Post https://api.github.com/graphql: Forbidden`；本助手未能创建 PR，不声称远端 CI 已执行。
- 准确 compare 入口：https://github.com/zhengxiangliu6-bit/Desktop-NOMI/compare/main...feat/stage2b-chat-integration?expand=1 。API 可访问且授权有效后可重试；临时说明文件丢失时依据本交接重建描述。
- 本记录另作后续文档提交并推送同一分支，最新提交见 `git log -1`。未合并、未发布、未调用真实收费模型。
