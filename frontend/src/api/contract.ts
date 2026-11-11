/** Mirrors the implemented backend Pydantic schema; checked against OpenAPI in integration tests. */
export const emotions = [
  "neutral",
  "happy",
  "sad",
  "curious",
  "surprised",
  "angry",
  "concerned",
] as const;
export type Emotion = (typeof emotions)[number];
export const motions = ["none", "nod", "tilt", "bounce"] as const;
export type Motion = (typeof motions)[number];
export const providers = ["mock", "openai"] as const;
export type Provider = (typeof providers)[number];
export const MAX_INPUT_CHARS = 4000;
export const MAX_REPLY_CHARS = 8000;
export interface ChatResponse {
  reply: string;
  emotion: Emotion;
  motion: Motion;
  session_id: string;
  provider: Provider;
}
export const errorStatuses = {
  FORBIDDEN: [403],
  SESSION_NOT_FOUND: [404],
  SESSION_BUSY: [409],
  PAYLOAD_TOO_LARGE: [413],
  UNSUPPORTED_MEDIA_TYPE: [415],
  VALIDATION_ERROR: [422],
  UPSTREAM_ERROR: [502],
  UPSTREAM_INVALID_RESPONSE: [502],
  CONFIGURATION_MISSING: [503],
  SESSION_LIMIT_REACHED: [503],
  UPSTREAM_TIMEOUT: [504],
  INTERNAL_ERROR: [500],
  HTTP_ERROR: [404, 405],
} as const;
export type ApiErrorCode = keyof typeof errorStatuses;
export const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
export const isUUID = (value: unknown): value is string =>
  typeof value === "string" &&
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
export function isChatResponse(value: unknown): value is ChatResponse {
  return (
    isRecord(value) &&
    typeof value.reply === "string" &&
    !!value.reply.trim() &&
    [...value.reply.trim()].length <= MAX_REPLY_CHARS &&
    emotions.includes(value.emotion as Emotion) &&
    motions.includes(value.motion as Motion) &&
    providers.includes(value.provider as Provider) &&
    isUUID(value.session_id)
  );
}
