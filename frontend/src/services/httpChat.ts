import { getLocalAuthorization } from "./localAuthorization";
import {
  errorStatuses,
  isChatResponse,
  isRecord,
  isUUID,
  MAX_INPUT_CHARS,
  type ApiErrorCode,
} from "../api/contract";
import type { ChatService } from "./chatService";
import { ChatServiceError } from "./chatErrors";

export function validateApiBase(base: string): string {
  const normalized = base.replace(/\/$/, "");
  if (!/^\/api(?:\/[a-zA-Z0-9_-]+)+$/.test(normalized))
    throw new Error("VITE_API_BASE_URL must be a same-origin /api/... path");
  return normalized;
}
export function createHttpChatService({
  baseUrl = "/api/v0",
  timeoutMs = 65000,
  fetcher = fetch,
}: {
  baseUrl?: string;
  timeoutMs?: number;
  fetcher?: typeof fetch;
} = {}): ChatService {
  const base = validateApiBase(baseUrl);
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0)
    throw new Error("Invalid HTTP timeout");
  return async (raw, signal, sessionId) => {
    const text = raw.trim();
    if (
      !text ||
      [...text].length > MAX_INPUT_CHARS ||
      (sessionId !== undefined && !isUUID(sessionId))
    )
      throw new ChatServiceError("VALIDATION_ERROR");
    if (signal.aborted) throw new DOMException("Cancelled", "AbortError");
    const request = new AbortController();
    const abort = () => request.abort();
    signal.addEventListener("abort", abort, { once: true });
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      request.abort();
    }, timeoutMs);
    try {
      const response = await fetcher(`${base}/chat`, {
        method: "POST",
        credentials: "omit",
        redirect: "error",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
          ...(getLocalAuthorization()
            ? { Authorization: `Bearer ${getLocalAuthorization()}` }
            : {}),
        },
        signal: request.signal,
        body: JSON.stringify({
          text,
          ...(sessionId ? { session_id: sessionId } : {}),
        }),
      });
      if (
        response.headers
          .get("content-type")
          ?.split(";")[0]
          ?.trim()
          .toLowerCase() !== "application/json"
      )
        throw new ChatServiceError("INVALID_RESPONSE");
      let value: unknown;
      try {
        value = await response.json();
      } catch {
        throw new ChatServiceError("INVALID_RESPONSE");
      }
      if (signal.aborted) throw new DOMException("Cancelled", "AbortError");
      if (timedOut) throw new ChatServiceError("CLIENT_TIMEOUT");
      if (!response.ok) {
        const error =
          isRecord(value) && isRecord(value.error) ? value.error : null;
        if (
          error &&
          typeof error.message === "string" &&
          typeof error.code === "string" &&
          Object.hasOwn(errorStatuses, error.code) &&
          isUUID(error.request_id) &&
          typeof error.retryable === "boolean" &&
          (
            errorStatuses[error.code as ApiErrorCode] as readonly number[]
          ).includes(response.status)
        ) {
          // Never display server-provided message or arbitrary headers/details.
          throw new ChatServiceError(
            error.code as ApiErrorCode,
            error.request_id,
          );
        }
        throw new ChatServiceError("INVALID_RESPONSE");
      }
      if (
        response.status !== 200 ||
        !isChatResponse(value) ||
        (sessionId && value.session_id !== sessionId)
      )
        throw new ChatServiceError("INVALID_RESPONSE");
      return {
        text: value.reply.trim(),
        emotion: value.emotion,
        motion: value.motion,
        provider: value.provider,
        sessionId: value.session_id,
      };
    } catch (error) {
      if (signal.aborted) throw new DOMException("Cancelled", "AbortError");
      if (timedOut) throw new ChatServiceError("CLIENT_TIMEOUT");
      if (error instanceof ChatServiceError) throw error;
      throw new ChatServiceError("NETWORK_ERROR");
    } finally {
      clearTimeout(timer);
      signal.removeEventListener("abort", abort);
    }
  };
}
