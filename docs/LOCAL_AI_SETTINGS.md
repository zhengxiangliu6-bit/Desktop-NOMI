# 阶段 2C：本地 AI 配置中心

本期只在可信本机开发 API 模式提供设置界面，不在 Pages 开启，不部署公网配置或 AI 服务。没有调用真实百炼账号。Windows 原生凭据存储和实际供应商 TLS/计费仍需在拥有者电脑验证，不能把替身测试当作实机通过。

## 风险审查与最小方案

原来的 loopback Host / Origin / CORS 不能单独授权密钥修改：普通本机程序能伪造这些头，公开网页也会尝试 CSRF 和 DNS 重绑定。因此增加一条默认关闭、显式启动的本地管理通道，而不是开放任意设置接口或引入账号系统。

- 在本机终端启动 `--enable-settings` 才生成随机的一次性配对码；码五分钟有效，最多五次尝试。它是短期本机授权，不是模型 Key，不要分享或粘贴到聊天/工单。
- 配对还要求实际 loopback 客户端、合法 Host、唯一 Origin、精确本机来源 `http://localhost:5173` 或 `http://127.0.0.1:5173`（并在后端允许列表中）、同源 Fetch Metadata；不接受 null Origin、重复头或远程来源。
- 配对成功换取随机能力 token，服务端只保留摘要，三十分钟失效。后续读取/更新/清除/测试都需要该 token 与来源检查，不依赖 CORS 单独判断。
- token 不是供应商 API Key，只保存在当前页面的 JS 内存，供设置和受管真实聊天使用，不放 localStorage/sessionStorage/cookie/URL。关闭面板仍可聊天；刷新页面或关闭标签会丢失授权，需要在本机重新启动授权通道获得新配对码。本期没有“记住登录”。
- 对设置中心管理的 OpenAI Provider，聊天也需配对授权，避免其他无授权本机进程消耗新存储凭据。原有环境注入的旧运行路径仍兼容原先本机信任模型，不声称本期把所有旧 API 变为多用户认证服务。
- 这是可信当前 OS 用户、可信 Vite/代码依赖与浏览器下的最小通道；不能抵御已控制同一用户账户的恶意软件、调试器、浏览器扩展或管理员。无法满足条件时不要启用配置通道，继续使用受控后端环境/Secrets。不是可对公网或局域网开放的管理服务。

## 在自己的 Windows 电脑使用（无需编辑模型 .env）

需要已安装项目所需 Python 3.12 / uv 和 Node.js。两终端运行：

```bash
# 仓库 backend 目录
uv sync --frozen --group dev
uv run --frozen python -m app.cli --enable-settings
```

```bash
# 仓库 frontend 目录
npm ci
npm run dev:api
```

`dev:api` 是跨平台 Node 启动器，直接选择本地 API 模式，不需要改 `.env`。默认仍监听 loopback，Vite 的 `/api` 代理到本机 8000；没有改变后端 Host/Origin 限制。普通 `npm run dev` 与所有生产构建继续是 Mock。

1. 在运行程序的电脑上打开 `http://127.0.0.1:5173/Desktop-NOMI/`，点击 **AI 设置**。
2. 从该后端终端复制本次配对码到配对输入框。配对码提交后也清空，不是 API Key。
3. Provider 选择 **OpenAI 兼容（阿里云百炼）**，选择自己账号地域对应的 Base URL，填写自己控制台的 Model ID；没有固定模型名称。
4. Key 操作选 **更新 Key**，只在 **API Key** 密码框输入真实值。不要把它放进模型 ID、URL、VITE_*、聊天、截图或日志。不要开启网络/HAR/调试录制，也不要让密码管理扩展保存该输入。
5. 点击 **保存配置**。输入框在请求完成前即清空；保存只写受保护配置并更新后端，不会请求供应商。新聊天立即使用新配置，无需重启；为避免把旧模型上下文转交新模型，会清空旧会话。
6. 更换入口时必须明确替换或清除 Key，不能把旧 Key 自动转发到新地域。只换模型时可以保留当前 Key。
7. 清除时选 **清除 Key** 再保存。窗口不会读回原文；页面重新读取或重新配对后也只显示“已配置/未配置”。

关闭设置面板保留当前页面短期授权；刷新后授权不恢复。重新配对目前需停止该后端、重新使用上述 flag 启动，保存的 Windows 配置仍在。这个重启用于重新授权，不是应用配置更新的要求。

### Windows 保存位置与其他平台

- Windows 使用当前用户的 **Windows Credential Manager Generic Credential**，目标名 `Desktop-NOMI/AIConfiguration/v1`；受保护记录含配置与 Key，不写明文 JSON、`.env`、仓库或临时文件。错误时失败关闭，不降级为文件保存。
- Windows CLI 正常启动会读取已保存记录；配置通道本身仍默认关闭。要使用受管真实聊天，需带 `--enable-settings` 启动并配对；只读取凭据不会自动产生供应商请求。
- 清除是把受保护记录覆盖为不含 Key 的配置，重启不会悄悄回退到旧环境 Key。无法读取/写入系统凭据时停止或返回安全错误，不输出 Win32 原始细节。
- 非 Windows 配置通道只用后端内存，不持久化任何 Key/配置；界面明确标注“重启清空”。云端仍可使用平台 Secrets/环境注入原路径。内存清除不能删除外部 Secret 绑定，重启可能重新注入，需在其安全设置中删除绑定。
- 运行模型时 Key 必须短暂存在后端内存、TLS 请求头以及用户提交时的浏览器内存中；Python/JS 不保证不可恢复的内存零化。系统凭据保护主要防止明文磁盘泄露，不隔离同用户恶意程序。

## Base URL 与 SSRF 边界

配置中心目前只允许以下精确 HTTPS API 根（可规范化末尾 `/`）：

- `https://dashscope.aliyuncs.com/compatible-mode/v1`
- `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- `https://dashscope-us.aliyuncs.com/compatible-mode/v1`

请以自己的百炼控制台地域、账号权限和官方文档为准；本次访问官方文档站被代理 403 拒绝，没有声称这些入口已在本环境实连通过。[官方兼容文档](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope)。其他区域/VPC/自定义兼容服务尚未审核，界面不能通过扩大白名单绕过限制；已有可信运维环境配置路径另行保留。

拒绝任意主机、IP、loopback/内网/元数据地址、额外端口、用户信息、query、fragment 和路径变体。实际连接时解析全部 DNS 地址，任一个非公网/多播就拒绝，并把验证后的数字 IP 固定到 TCP 连接；HTTP/TLS 仍保留原主机名用于 Host、SNI 和证书验证，避免检查与连接之间再次解析带来的 DNS 重绑定。只请求精确 `/compatible-mode/v1/chat/completions`，不跟随重定向、不自动重试。

受管连接不静默绕过系统/环境代理。如果存在代理而无法保持 IP 固定保证，返回 `SECURE_TRANSPORT_UNAVAILABLE`，不调用供应商。企业代理和本云环境目前不支持此安全直连路径；不要通过关闭环境网络策略来“修复”，应使用受控环境注入路径或等待专项代理支持。当前受管设置功能优先面向可直接联网的可信 Windows 本机。

## 明确授权的单次连接测试

先保存配置，再勾选 **我明确授权本次连接测试，真实 Provider 可能产生费用**，点击 **测试连接（单次）**。

后端核对当前配置 revision、有效授权和 `confirm_paid_request` 必须为 JSON true；同一时间只允许一个测试，配置变化/未保存时不能测试。一次点击只发一次短提示请求，不读取聊天历史，不自动重试；输出 token 参数最多 256，不代表供应商总费用保证。返回只有 ok/provider/revision，不返回模型文本或供应商原始错误。

测试验证 `/chat/completions` 拼接、所选模型与 token 参数、可选 JSON Object，以及严格 reply/emotion/motion 输出。Provider 默认发 `max_tokens`，也可显式选择 `max_completion_tokens`；JSON Object 模式需该模型支持，不能假设所有百炼模型、尤其推理模型都支持同一组合。截断、未知枚举、错误结构、认证/参数错误与超时分别安全报告；不要自动再次付费试错。需要额外供应商参数的模型仍需后续兼容工作，当前不猜测模型名称或能力。

Mock Provider 的测试只验证本地流程，不访问供应商。保存、清除、读取和页面打开都不会做连接测试。真实 Key、账号、TLS/计费与模型实测本次全部未执行；应由拥有者在自己的电脑明确点击授权后验证。

## 浏览器与 Pages 隔离

API Key 用非受控密码输入框暂存，不进入 React 持久 state、浏览器存储、URL 或日志；提交立即清空，错误时也不恢复。浏览器开发者工具、扩展或主动 HAR/录屏能采集用户提交的数据，应用不能阻止主动采集，因此真实凭据操作不要启用这些工具。

生产构建彻底剔除设置实现，不只是隐藏按钮；Pages 无设置字段、配置请求或真实 Key。自动化检查生成 JS 不含 `/api/v0/settings`、配对字段或付费测试标记，并验证页面没有 AI 设置按钮/API Key 框。测试只使用虚构凭据，不开启设置流程的 trace、截图、视频或网络附件。

## 验收与剩余限制

完整命令沿用 INTEGRATION：前端 typecheck/unit/build、Mock Playwright、Pages 静态、实际 FastAPI 集成；后端 pytest/Ruff。新增授权/来源/私网 DNS、存储回滚、保存清除、热更新、token 失效、显式测试和 Key 不返回/不记录测试。Windows API 使用替身验证调用与覆盖流程，**Windows 原生凭据保护、实际百炼、原生 TLS 和计费均未验证**。

没有语音、长期记忆、硬件、公网认证系统或公网后端。后端仍单 worker，会话在内存中；修改配置有在途聊天时拒绝更新，而不是让密钥切换影响旧请求。具体执行结果见 HANDOFF。
