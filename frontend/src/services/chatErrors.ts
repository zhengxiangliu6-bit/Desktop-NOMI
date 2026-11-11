import type { ApiErrorCode } from "../api/contract";
export type ChatErrorCode =
  | ApiErrorCode
  | "NETWORK_ERROR"
  | "CLIENT_TIMEOUT"
  | "INVALID_RESPONSE"
  | "MOCK_ERROR";
const messages: Record<ChatErrorCode, string> = {
  SESSION_NOT_FOUND: "会话已失效或后端已重启，请主动开始新会话。",
  SESSION_BUSY: "当前会话仍在处理请求，请稍后手动再试，不会自动重试。",
  UPSTREAM_TIMEOUT: "模型服务响应超时，请稍后手动再试。",
  UPSTREAM_ERROR: "模型服务请求失败，请检查后端服务配置或稍后再试。",
  UPSTREAM_INVALID_RESPONSE: "模型回复格式错误，本轮没有加入成功记录。",
  CONFIGURATION_MISSING: "后端模型配置缺失，请在后端检查配置。",
  NETWORK_ERROR: "无法连接对话服务，请检查网络和后端是否启动。",
  CLIENT_TIMEOUT: "等待服务超时，提交结果未知；后端可能仍在处理。",
  INVALID_RESPONSE: "服务返回非预期格式，请检查后端是否启动、代理地址和服务版本。",
  FORBIDDEN: "后端拒绝当前来源，请检查同源开发代理配置。",
  PAYLOAD_TOO_LARGE: "请求过长，请缩短后重试。",
  UNSUPPORTED_MEDIA_TYPE: "请求格式不受支持，请检查客户端与服务版本。",
  VALIDATION_ERROR: "输入或会话格式不合法，请检查后重试。",
  SESSION_LIMIT_REACHED: "服务会话容量已满，请稍后再试。",
  INTERNAL_ERROR: "对话服务内部错误，请稍后再试。",
  HTTP_ERROR: "对话接口路径或方法不可用，请检查代理配置。",
  MOCK_ERROR: "这是一次模拟故障。点击「恢复待机」后，可以重新发送消息。",
};
export class ChatServiceError extends Error {
  constructor(
    readonly code: ChatErrorCode,
    readonly requestId: string | null = null,
  ) {
    super(messages[code]);
    this.name = "ChatServiceError";
  }
}
export const UNKNOWN_RESULT_NOTICE =
  "已停止等待，不能确认后端是否停止或已完成。再次请求真实模型可能重复计费；必要时开始新会话。";
export function safeChatError(error: unknown): ChatServiceError {
  return error instanceof ChatServiceError
    ? error
    : new ChatServiceError("NETWORK_ERROR");
}
