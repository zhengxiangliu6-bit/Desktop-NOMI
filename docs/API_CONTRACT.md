# 后端 API 契约：阶段 2A

状态：已实现并以 pytest / 本地 HTTP 验证，真实模型账号验证未执行。阶段 1 前端及 Pages 仍调用自己的本地 Mock，**未接入本服务**。基础路径 `/api/v0`，UTF-8 JSON，字段 snake_case。

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

实现入口为 `backend/app/domain/models.py` 和 `api/routes.py`，应用运行时 `/openapi.json` 为可执行 schema。未来 2B 需要显式设计前端 API Client、部署连接和 error/enum 映射；不得因已有 motion 字段就驱动设备。SQLite、turn_id/幂等、语音与长期记忆仍为后续范围。
