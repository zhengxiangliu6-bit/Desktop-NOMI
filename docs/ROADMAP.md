# V0 路线图

阶段按依赖顺序推进，每次任务只实现明确授权阶段。V0.0 已交付，阶段 1 前端 Mock 原型已实现；阶段 2A 已交付后端基础与 health，2B 已完成 Mock Provider 的 HTTP 集成，Windows 实机和真实模型验证尚未完成。以下全栈阶段验收门槛不因此视为全部通过。

| 阶段 | 范围 | 验收标准 |
| --- | --- | --- |
| V0.0 架构基线 | 规范、模块、契约、依赖与许可调研 | 文件齐备；相对链接、配置与设计一致；无业务代码；独立分支和 PR（权限阻塞需记录） |
| V0.1 工程骨架与表情 | React 19 / TS / Vite、FastAPI、配置加载、health、Expression Adapter；最小表情验证入口 | 锁文件可重复安装；构建/类型检查通过；health 契约测试；切换 idle/happy/thinking 与未知值降级；reduced-motion 和组件卸载清理测试；Windows 浏览器实测记录 |
| V0.2 文字对话 | session CRUD、非流式消息、OpenAI 兼容 Adapter、SQLite | mock 端到端走通；配置更换模型与 URL 无需改代码；缺配置/超时/409/幂等/重启 interrupted 测试；Key 不进入前端和日志；显式授权后才做真实供应商烟测 |
| V0.3 情绪联动 | 情绪候选解析、校验、TTL、优先级、取消与旧结果隔离 | 核心映射与每条状态迁移自动化测试；非法候选回退 neutral；工作态覆盖、TTL 到期、乱序与取消均有测试；文字 UI 可表达错误 |
| V0.4 可替换语音 | 选定并记录一种 STT 与 TTS 实现、浏览器录音/播放、文字降级 | mock 识别→对话→合成端到端；适配器替换测试；大小/MIME/超时错误；Windows 真实麦克风、权限拒绝、无设备、扬声器、播放阻止与停止均人工验收；录音默认不落盘 |
| V0.5 Windows V0 验收 | 开发启动说明、数据清理、Null / Mock Device Adapter、回归与许可检查 | 干净 Windows 环境按文档启动；会话重启恢复/删除和 30 天清理测试；硬件关闭且无网络设备副作用；全链路文字/语音回归记录、依赖许可证清单与署名齐备 |

## 阶段 1 前端原型（本次授权）

范围为 Aora 角色、响应式聊天外壳、明显标识的 Mock Service、阶段/情绪分离、取消与错误恢复、调试面板。无 Python 后端、真实 AI、录音或声音。此实现不等于完成真实文字对话与模型情绪解析阶段。

验收命令：`cd frontend` 后依次 `npm ci`、`npm run typecheck`、`npm test`、`npm run build`；浏览器验收 `npm run test:e2e`（先安装 Playwright Chromium，或配置已有 Chromium 路径）。Windows 手动步骤见 README。本次执行结果与限制见 HANDOFF。

## 阶段 2A 独立后端（本次授权）

已实现 FastAPI health/chat、环境配置、Mock/OpenAI 兼容 Provider、严格 reply/emotion/motion 输出校验、请求/超时/格式错误区分及有界进程内上下文。验收为无 Key 的 pytest、MockTransport、错误恢复/长度限制、真实本地 HTTP 烟测，以及前端和 Pages 无变更。真实供应商账号验证未执行。

阶段 2A 不含前端集成；阶段 2B 已补开发代理与 API Client，仍不实现 SQLite、turn_id/幂等、语音、动作执行或公网后端。原 V0.2 全量验收不能因 2A 完成而标为通过。

## 阶段 2B 前后端集成（本次交付）

统一 Mock/HTTP Chat Service、配置可见模式、会话连续与主动重建、请求取消/迟到隔离、严格消费当前契约、错误恢复与情绪映射；Pages 生产强制 Mock。验收包括前端 typecheck/unit/build、Mock 浏览器、Pages 静态回归、后端 pytest/Ruff、共享契约和实际 FastAPI + Mock Provider 的 HTTP 集成。

阶段 2C 再对真实供应商进行明确授权与预算下的最小实测，验证账号、参数、计费和结构化响应稳定性。本次真实账号、模型调用及公网部署未执行；2B HTTP Mock 成功不能替代 2C 验证。

## 阶段 2C 本地 AI 配置中心（本次交付）

终端配对、受保护设置/短期授权、Windows Credential Manager 与非 Windows 内存、严格百炼地址/公网 IP 固定、配置热更新、明确单次连接测试、生产剔除与泄露回归。真实百炼、Windows 原生与费用验证未执行；只能由拥有者在可信本机明确授权后单次验证，不自动进入语音、记忆、硬件或公网部署。

## 测试责任

单元：后端 pytest，前端 Vitest；组件 React Testing Library；跨端 `tests/contract/` 验证 JSON 字段、枚举、错误与二进制响应；Playwright 验证浏览器流程。CI 到 V0.1 随真实工程建立。核心状态和适配器逻辑必须自动化测试，不用真实付费调用替代 mock 测试。

Linux 云端可验证构建、契约、mock 与浏览器逻辑；不能据此声称 Windows 驱动、实体麦克风/扬声器、系统权限或未来舵机已通过。Windows 验收需记录系统/浏览器版本、操作、预期、实际与证据，不提交私人音频。

## V0 之外

长期记忆检索、主动提醒与人格策略、唤醒词/常驻监听、流式输出、桌面壳/安装包、ESP32-S3 传输与真实控制均需新阶段设计和验收。商业发布前由拥有者确认 Aora 授权、项目许可、品牌及语音供应商数据条款。
