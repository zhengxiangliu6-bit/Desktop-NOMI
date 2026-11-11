# 历史设计草案（归档，非当前已实现契约）

以下保留阶段 0 的全栈规划原稿，便于未来评审 SQLite、turn_id、语音与会话管理。原稿里的“当前”“尚未实现”是当时状态，不是阶段 2A 的现状。**当前已实现接口与回复结构以 [API_CONTRACT](../API_CONTRACT.md) 为准**；归档中的 `/sessions` 路由、Emotion 对象、TurnResult、幂等与持久化均未在 2A 实现，不能据此接入前端。

---

# 前后端接口契约 v0（设计稿）

所有 HTTP 端点尚未实现；阶段 1 前端只调用本地 Mock Service，不发出 API 请求、不要求凭据。Mock 的 listening/speaking 是无语音展示，angry 为本地演示扩展，不作为 HTTP 协议变更；本契约仍按后续 ROADMAP 阶段交付。基础路径 `/api/v0`，UTF-8 JSON、字段 snake_case、时间 RFC3339 UTC（`Z`）。ID 使用 UUID 字符串；客户端生成 turn_id，服务端生成其余 ID。未知请求字段拒绝；消费者忽略新增响应字段。无认证仅限本机原型，网络安全边界见 ARCHITECTURE。

## 通用对象

`Session = {id: UUID, created_at: timestamp}`。

`Message = {id: UUID, session_id: UUID, turn_id: UUID, role: "user" | "assistant", text: string, created_at: timestamp}`。text 去除首尾空白后非空，用户最多 4000 Unicode 码点，助手最多 8000；超长助手输出作为 UPSTREAM_INVALID_RESPONSE，不静默截断。system 消息为后端配置，客户端不能伪造。

`Emotion = {schema_version: 1, name: "neutral" | "happy" | "sad" | "curious" | "surprised" | "concerned", intensity: number, ttl_ms: integer, source: "model" | "fallback"}`。

intensity 必须是有限数且在 0..1；ttl_ms 为 500..10000，默认 3000。缺失/非法候选整对象回退 `{schema_version:1,name:"neutral",intensity:0,ttl_ms:3000,source:"fallback"}`。有效候选由服务端补 schema_version/source；客户端不信任越界响应，降级 neutral。emotion 属于助手回复，不是用户心理诊断；上游 emotionId 不进入本协议。

`TurnResult = {turn_id: UUID, user_message: Message, assistant_message: Message, emotion: Emotion}`。成功结果整体返回，不发送 token 流。

## 端点

| 阶段 | 方法与路径 | 输入 | 成功响应 |
| --- | --- | --- | --- |
| V0.1 | GET /health | 无 | 200 Health |
| V0.2 | POST /sessions | JSON `{}` | 201 Session |
| V0.2 | GET /sessions/{session_id}/messages | limit 默认20，1..100；before 可选消息 UUID | 200 `{items: Message[], next_before: UUID或null}` |
| V0.2 | DELETE /sessions/{session_id} | 无 | 204 无 body |
| V0.2 | POST /sessions/{session_id}/messages | `{turn_id: UUID, text: string}` | 200 TurnResult |
| V0.4 | POST /speech/transcriptions | 原始音频 body，Content-Type 见下 | 200 `{text:string, language:string或null}` |
| V0.4 | POST /speech/synthesis | `{text:string, voice?:string, language?:string}` | 200 原始音频，Content-Type `audio/wav` |

health 返回 `{status:"ok", api_version:"v0", capabilities:{chat:boolean, stt:boolean, tts:boolean, device:false}}`。健康检查不请求供应商、不暴露 Key、Base URL 或模型配置；能力 true 只说明本地配置已具备，不保证远端可用。chat 缺配置时 false，服务仍可用于表情；调用 chat 返回 CONFIGURATION_MISSING。

消息列表为成功消息，按 `(created_at,id)` 升序。分页先选 before 之前最近 limit 条，再升序返回；尚有更早消息时 next_before 为本页最早消息 id，否则 null。未知会话或 before 不属于该会话返回 404。V0 不提供会话列表，前端仅在本地保存当前 session_id，不在 localStorage 存对话文本；删除后清除该 ID。

DELETE 在会话有在途 turn 时返回 409 SESSION_BUSY，不会一边删除一边重建。不存在会话返回 404。成功删除级联清除 messages 和 turns。

## 文字请求与结果示例

```json
{
  "turn_id": "00000000-0000-4000-8000-000000000003",
  "text": "今天我们学什么？"
}
```

```json
{
  "turn_id": "00000000-0000-4000-8000-000000000003",
  "user_message": {
    "id": "00000000-0000-4000-8000-000000000004",
    "session_id": "00000000-0000-4000-8000-000000000001",
    "turn_id": "00000000-0000-4000-8000-000000000003",
    "role": "user",
    "text": "今天我们学什么？",
    "created_at": "2026-11-11T07:00:00Z"
  },
  "assistant_message": {
    "id": "00000000-0000-4000-8000-000000000005",
    "session_id": "00000000-0000-4000-8000-000000000001",
    "turn_id": "00000000-0000-4000-8000-000000000003",
    "role": "assistant",
    "text": "一起了解机器人的表情吧。",
    "created_at": "2026-11-11T07:00:01Z"
  },
  "emotion": {
    "schema_version": 1,
    "name": "curious",
    "intensity": 0.6,
    "ttl_ms": 3000,
    "source": "model"
  }
}
```

同一会话仅一个 pending turn。相同 turn_id + 相同规范化 text：成功则重放原结果，处理中返回 TURN_IN_PROGRESS；相同 ID 不同 text 返回 TURN_CONFLICT。不同 ID 遇忙返回 SESSION_BUSY。失败记录返回原错误，重试失败操作需新 ID；进程重启后残留 pending 变为 TURN_INTERRUPTED，不擅自重复扣费。以上保证本地去重，不保证供应商 exactly-once。记录生命周期随会话删除/清理终止。V0 无服务端取消端点，前端取消只停止等待和播放；后端可能继续保存结果。

## 语音细则（V0.4）

STT 请求为单段原始音频，无 multipart；接受 `audio/webm`（可带 `codecs=opus`）与 `audio/wav`，最长 30 秒、最大 10 MiB。后端校验大小、实际容器和时长，不只信任后缀；不支持编码为 415，超限为 413。浏览器需检测 MediaRecorder 支持格式；无法录制支持格式时退回文字，不在此阶段擅自加转码依赖。识别为空时 200 text 为 `""`，前端回 idle，不发起聊天。

TTS text 非空且最多 2000 码点；超长助手消息仍展示全文，跳过语音并显示提示。voice / language 为供应商适配器可接受的可选标识，未知值 422；默认来自后端配置。音频统一输出 WAV（原生支持或由选定 Adapter 转换），最大 10 MiB、30 秒；供应商无法满足则返回 UPSTREAM_INVALID_RESPONSE。前端用 Blob URL 播放并及时 revoke，响应为 `Cache-Control: no-store`。二进制成功与 JSON 错误按 HTTP 状态及 Content-Type 区分。原始音频不写 SQLite，失败也不保存文件。

语音开关默认 disabled，无供应商实现时 503 FEATURE_DISABLED。STT/TTS 只返回文本/音频，不创建消息、不自动调用 LLM；前端负责串联且复用相同文字消息端点。

## 错误、超时与重试

所有 JSON 和音频端点的非成功响应均为 `application/json`：

```json
{
  "error": {
    "code": "UPSTREAM_TIMEOUT",
    "message": "服务响应超时，请稍后重试。",
    "request_id": "00000000-0000-4000-8000-000000000009",
    "retryable": true
  }
}
```

所有响应携带 `X-Request-ID`，前端跨域允许读取；错误 ID 与该头一致。不可回传上游原始错误、Key、调用栈或对话片段。

| HTTP | code | retryable |
| --- | --- | --- |
| 404 | SESSION_NOT_FOUND / MESSAGE_NOT_FOUND | false |
| 409 | SESSION_BUSY / TURN_IN_PROGRESS | true |
| 409 | TURN_CONFLICT / TURN_INTERRUPTED | false |
| 413 | PAYLOAD_TOO_LARGE | false |
| 415 | UNSUPPORTED_MEDIA_TYPE | false |
| 422 | VALIDATION_ERROR | false |
| 429 | RATE_LIMITED | true |
| 502 | UPSTREAM_ERROR / UPSTREAM_INVALID_RESPONSE | true |
| 503 | CONFIGURATION_MISSING / FEATURE_DISABLED | false |
| 504 | UPSTREAM_TIMEOUT | true |
| 500 | INTERNAL_ERROR | false |

retryable 表示用户可选择重试，不授权自动重发付费操作；429 可含 Retry-After 秒数。FastAPI 默认 422 需转换为本结构。未知 Origin/Host 返回 403 FORBIDDEN（retryable false）。LLM 超时 60 秒、STT/TTS 30 秒；前端各留 5 秒余量。全局 JSON body 上限 64 KiB，音频上限 10 MiB。

## 版本演进与验收

本契约为先行设计，V0.1 开始以 Pydantic schemas / OpenAPI 与前端类型测试落实；生成文件不得替代设计审查。破坏变更升级路径版本，并同步架构、测试、示例和 HANDOFF。V0.2 neutral fallback 先行，V0.3 增加模型情绪候选解析，不改变 TurnResult。STT/TTS 的真实供应商及依赖在 V0.4 验证后锁定。记忆、主动交互和设备 HTTP 端点本次不定义。
