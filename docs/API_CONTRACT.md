# 后端 API 契约：阶段 2A / 2B 消费者

状态：已实现并以 pytest / 本地 HTTP 验证，真实模型账号验证未执行。阶段 2B 在显式 api 开发模式中经同源代理接入；默认前端与 Pages 仍为纯 Mock。基础路径 `/api/v0`，UTF-8 JSON，字段 snake_case。

旧的全栈设计保留为 [历史规划](design/API_V0_PLANNED.md)，其中 `/sessions`、turn_id、SQLite、语音等均未实现。2A 新增独立 `/chat`，不将旧草案中的 Emotion 对象 / TurnResult 冒充当前响应；2B 应以本文与当前 OpenAPI 为入口。

## GET /api/v0/health

成功 200：

```json
{
  "status": "ok",
  "api_version": "v0",
  "provider": "mock",
  "capabilities": {"chat": true, "stt": false, "tts": false, "device": false}
}
```

不请求模型，不泄露 Key、Base URL 或模型名。provider 是 `mock | openai`，明确标识模式。chat=true 只说明 Mock 可用或 OpenAI 配置已齐全，不代表已验证远端账号或模型。OpenAI 配置缺失时 health 仍为 200，但 chat=false，调用 chat 返回 503；不会自动降级成 Mock。

## POST /api/v0/chat

Content-Type 必须是 `application/json`。新会话省略 session_id（或给 null）；续聊使用之前返回的 UUID。

```json
{"text": "你好"}
```

成功 200：

```json
{
  "reply": "[Mock] 我收到你的消息了，很高兴陪着你。",
  "emotion": "happy",
  "motion": "nod",
  "session_id": "00000000-0000-4000-8000-000000000001",
  "provider": "mock"
}
```

续聊请求示例：

```json
{"text": "今天有点累", "session_id": "00000000-0000-4000-8000-000000000001"}
```

| 字段 | 约束 |
| --- | --- |
| text | 必须是字符串；去首尾空白后 1..4000 Unicode 码点；禁止客户端提供 system / assistant role |
| session_id | 请求中可省略/null，否则必须为 UUID；未知、过期或重启前的 ID 返回 404，不静默新建 |
| reply | 模型 JSON 中必须为字符串，去首尾空白后 1..8000 码点 |
| emotion | `neutral / happy / sad / curious / surprised / angry / concerned` |
| motion | `none / nod / tilt / bounce`，仅描述性元数据，不执行本机/舵机/设备操作 |
| provider | `mock / openai`，来自服务配置，不由模型输出决定 |

模型只允许输出 `{reply, emotion, motion}` 三个字段；必须是一个 JSON 对象，不接受 Markdown 代码围栏、额外字段、未知枚举、空回复、数字/对象冒充字符串或 tool/function calls。Pydantic 严格校验失败，整个本轮返回 `UPSTREAM_INVALID_RESPONSE`，不返回半有效结果，不将失败输入或输出加入上下文。**这有意取代旧草案的非法情绪 neutral 静默降级策略**，以满足阶段 2A 的结构化校验与错误区分要求。

motion 不含脚本、命令、路径或硬件参数。即使 reply 文本提及操作，也只作为文本返回；服务没有执行器、工具注册或硬件连接。

## 上下文、并发与恢复

- 当前仅单进程内存，CLI 强制单 worker；重启清空，不提供数据库、长期记忆、消息列表、会话删除或导出接口。
- 默认最多 100 个会话，空闲 1800 秒后失效（下次聊天请求时清理，忙碌会话不被清理）。同会话最多一个在途请求，冲突 409；不同会话隔离。
- 默认每次模型请求包含固定 system、最多最近 9 个完整成功轮次及本轮 user（`NOMI_CONTEXT_MAX_TURNS=10`，包含本轮）。仅成功校验后原子追加 user/assistant 对。
- 上下文总长度默认 16000 Unicode 码点，包括 system、用户文本和已校验助手 JSON；这是字符预算，**不是精确 token 计数**。从最旧历史起裁剪，保留连续最新完整轮次；本轮 user 和 system 始终保留。若单轮成功输出过大导致整个历史对超预算，仍返回成功回复，但不保留该轮历史。
- 有界历史按 max_turns 与 max_chars 双重限制；模型输出另受 max_tokens、回复 8000 字和上游响应 128 KiB 限制。特定模型的实际 token 上下文可能更小，需配置匹配供应商。
- 超时、网络/HTTP 错误、格式错误均释放会话占用，原成功历史不被污染。失败的新匿名会话会删除，避免占满容量。
- 总调用期限默认 60 秒，包含上游响应读取；没有自动重试，也无幂等或服务端取消端点。客户端重试可能重复计费；取消不能保证供应商停止生成。应由用户明确决定是否重试。

## 错误契约

服务错误结构及 OpenAPI 422 错误 schema 均使用 ErrorEnvelope；不回传原始上游错误、输入、Key 或调用栈。响应头携带新生成的 `X-Request-ID`，与错误对象一致；`Cache-Control: no-store`。

```json
{
  "error": {
    "code": "UPSTREAM_TIMEOUT",
    "message": "模型服务响应超时，请稍后重试。",
    "request_id": "00000000-0000-4000-8000-000000000009",
    "retryable": true
  }
}
```

| HTTP | code | 含义 | retryable |
| --- | --- | --- | --- |
| 403 | FORBIDDEN | 不允许的 Host / Origin | false |
| 404 | SESSION_NOT_FOUND | 未知、过期或重启前会话 | false |
| 409 | SESSION_BUSY | 同会话已有在途请求 | true |
| 413 | PAYLOAD_TOO_LARGE | 请求超过 64 KiB | false |
| 415 | UNSUPPORTED_MEDIA_TYPE | POST 非 JSON | false |
| 422 | VALIDATION_ERROR | 请求 JSON、字段、UUID、类型或长度非法 | false |
| 502 | UPSTREAM_ERROR | 网络连接/协议失败、上游非 2xx（含认证、429、重定向）；不转发其私密 body | true |
| 502 | UPSTREAM_INVALID_RESPONSE | envelope/结构化 JSON/枚举无效、截断、tool calls 或上游超过大小限制 | true |
| 503 | CONFIGURATION_MISSING | 显式 OpenAI 模式缺少 Base URL / Key / Model | false |
| 503 | SESSION_LIMIT_REACHED | 未过期会话已达容量 | true |
| 504 | UPSTREAM_TIMEOUT | HTTP 超时或总调用期限超时 | true |
| 500 | INTERNAL_ERROR | 未预期的内部异常，已脱敏 | false |
| 404 / 405 | HTTP_ERROR | 未实现路径 / 不允许的方法 | false |

retryable 仅表示可由用户选择重试，不等于应该自动重试；认证/参数错误通常需先修复配置。CORS OPTIONS 预检由标准 CORS 中间件处理；该表针对实际服务请求。

## 边界与版本

默认只绑定 loopback，校验 Host 为 localhost/127.0.0.1/::1；来源为精确配置列表，禁止通配、credentials 默认关闭。不提供认证，不能当作可公开部署服务；Pages 未获后端接入权限，本阶段不放开其 Origin。

实现入口为 `backend/app/domain/models.py` 和 `api/routes.py`，应用运行时 `/openapi.json` 为可执行 schema。阶段 2B 已实现开发用 HTTP Client、会话/错误恢复和 emotion 映射，未部署公网后端；不得因已有 motion 字段就驱动设备。SQLite、turn_id/幂等、语音与长期记忆仍为后续范围。

## 阶段 2B 客户端补充（HTTP 契约未变）

前端只构造 text 和可选 session_id；成功响应需验证 reply、emotion、motion、UUID、provider 和 200 状态，续聊响应不能偷偷替换 ID。成功成对保存记录，失效会话需用户主动新建。模式与 Provider 分开显示；motion 只作描述，不直接映射到执行器。

错误 body 的 message 仅用于服务端契约，前端不直接显示它，而按经过检查的 code/status 使用固定安全文案。网络错误、客户端等待超时和非 JSON/非法响应为客户端本地错误，不是新增后端状态码；未知提交结果和取消都不保证服务端停止，也不自动重试。

Pydantic schema 快照为 contracts/chat-v0.json，由 backend/scripts/export_contract.py 生成，后端与前端测试分别检查与实际模型和消费类型一致。字段与路由没有变更，不使用归档中的 sessions/turn_id。具体开发边界见 [INTEGRATION](INTEGRATION.md)。

## 阶段 2C：本机受保护配置接口

默认关闭，由 CLI `--enable-settings` 启用；只接受可信 loopback 开发来源和配对授权，不能仅靠 CORS。原有 chat JSON 字段未变；**受管 openai 配置的 chat 额外要求本次配对 Bearer token**，缺失时 403 FORBIDDEN，不发供应商请求。Mock 不新增授权要求。

| 方法/路径 | 请求 | 响应 |
| --- | --- | --- |
| POST /api/v0/settings/pair | `{code:string}`（终端一次性码） | `{token:string, expires_in:1800}`，这是短期本机能力，不是模型 Key |
| POST /api/v0/settings/read | `{}` + Bearer | 非敏感配置、key_configured、storage、revision、connection、allowed_base_urls；无 api_key 字段 |
| PUT /api/v0/settings | ProfileUpdate + Bearer | 同上；保存后清空旧会话，连接状态回到未测试 |
| POST /api/v0/settings/test | `{revision:integer,confirm_paid_request:true}` + Bearer | `{ok:true,provider,revision}`，一次调用，不返回模型文本 |

敏感读取使用 POST，以便浏览器稳定发送 Origin；没有匿名 GET 设置读取。所有操作检查唯一 Host/Origin、真实 loopback peer、精确本地来源、同源 Fetch Metadata；除配对外需有效随机 Bearer。配对码五分钟、最多五次尝试、单次使用；能力三十分钟，刷新不恢复。

ProfileUpdate 仅允许 provider(mock/openai)、base_url、model、key_action(keep/replace/clear)、可选 api_key、max_tokens(64..8192)、token_parameter(max_tokens/max_completion_tokens)、json_mode。openai 要求受支持的非空入口/模型；Key 可稍后填写，缺失时不能连接。keep 不接受新 Key；replace 必须有合法新 Key；clear 不能同时发送新 Key。更换入口须明确 replace/clear，不能复用旧 Key。Key 从不进入读取响应、错误原文或日志。

新增安全错误沿用 ErrorEnvelope：403 SETTINGS_DISABLED/SETTINGS_FORBIDDEN；409 CONFIGURATION_BUSY/KEY_SCOPE_CHANGED；503 CREDENTIAL_STORAGE_ERROR/SECURE_TRANSPORT_UNAVAILABLE；422 VALIDATION_ERROR。测试上游错误沿用 UPSTREAM_ERROR/TIMEOUT/INVALID_RESPONSE。连接测试 revision 不匹配、并发或无字面 true 授权时不调用供应商。配置更改成功后新请求立即用新快照，忙碌时拒绝更新。

公开凭据状态仅 key_configured(bool)；storage 为 windows-credential-manager 或 memory-only；connection 为 not_tested 或 verified。Windows 原生存储、SSRF 策略、代理限制、刷新重配对与单次付费测试详见 [LOCAL_AI_SETTINGS](LOCAL_AI_SETTINGS.md)。当前仅桌面开发的可信本机界面，没有公网配置通道。
