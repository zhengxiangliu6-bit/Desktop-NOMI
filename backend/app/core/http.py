import logging
import time
from urllib.parse import urlsplit
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.errors import AppError

MAX_BODY_BYTES = 64 * 1024
logger = logging.getLogger("nomi.requests")


def error_response(error: AppError, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=error.status,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "request_id": request_id,
                "retryable": error.retryable,
            }
        },
    )


class LocalHTTPBoundary:
    """Loopback prototype protection, bounded input and sanitized error/trace metadata."""

    def __init__(self, app: ASGIApp, settings: Settings, local_admin=None):
        self.app = app
        self.settings = settings
        self.local_admin = local_admin

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = False
        status = 500
        start_time = time.monotonic()

        async def traced_send(message: Message) -> None:
            nonlocal started, status
            if message["type"] == "http.response.start":
                started = True
                status = message["status"]
                headers = list(message.get("headers", []))
                headers.extend(
                    [(b"x-request-id", request_id.encode()), (b"cache-control", b"no-store")]
                )
                message = {**message, "headers": headers}
            await send(message)

        async def reject(error: AppError) -> None:
            await error_response(error, request_id)(scope, receive, traced_send)

        try:
            headers = {
                key.decode("latin-1"): value.decode("latin-1")
                for key, value in scope.get("headers", [])
            }
            try:
                host_url = urlsplit("http://" + headers.get("host", ""))
                _ = host_url.port
                host = host_url.hostname
                if (
                    host_url.username
                    or host_url.password
                    or host_url.path
                    or host_url.query
                    or host_url.fragment
                ):
                    host = None
            except ValueError:
                host = None
            origin = headers.get("origin")
            if host not in {"localhost", "127.0.0.1", "::1"} or (
                origin is not None and origin not in self.settings.allowed_origins
            ):
                await reject(AppError(403, "FORBIDDEN", "不允许的 Host 或 Origin。"))
                return
            if scope["path"].startswith("/api/v0/settings"):
                try:
                    if self.local_admin is None or not self.local_admin.enabled:
                        raise AppError(
                            403,
                            "SETTINGS_DISABLED",
                            "请在本机终端使用 --enable-settings 启用配置。",
                        )
                    self.local_admin.boundary(scope, headers, scope["path"])
                except AppError as error:
                    await reject(error)
                    return
            if (
                scope["path"] == "/api/v0/chat"
                and self.local_admin is not None
                and self.local_admin.profile.managed
                and self.local_admin.profile.provider == "openai"
            ):
                try:
                    self.local_admin.boundary(scope, headers, scope["path"])
                except AppError:
                    await reject(AppError(403, "FORBIDDEN", "请先在本地 AI 设置完成配对。"))
                    return
            upstream_receive = receive
            if scope["method"] in {"POST", "PUT"}:
                content_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if content_type != "application/json":
                    await reject(
                        AppError(415, "UNSUPPORTED_MEDIA_TYPE", "请求必须使用 application/json。")
                    )
                    return
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > MAX_BODY_BYTES:
                        await reject(AppError(413, "PAYLOAD_TOO_LARGE", "请求超过 64 KiB。"))
                        return
                    if not message.get("more_body", False):
                        break
                delivered = False

                async def buffered_receive() -> Message:
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": bytes(body), "more_body": False}
                    return await receive()

                upstream_receive = buffered_receive
            await self.app(scope, upstream_receive, traced_send)
        except Exception:
            # Do not log exception strings, bodies, URLs, credentials or provider errors.
            if started:
                raise RuntimeError("Response stream failed") from None
            await reject(AppError(500, "INTERNAL_ERROR", "服务内部错误。"))
        finally:
            logger.info(
                "request_id=%s status=%s elapsed_ms=%.1f",
                request_id,
                status,
                (time.monotonic() - start_time) * 1000,
            )
