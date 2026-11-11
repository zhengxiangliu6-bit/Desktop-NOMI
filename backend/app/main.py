from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from app.adapters.llm.base import ChatProvider
from app.adapters.llm.mock import MockProvider
from app.adapters.llm.openai import OpenAIProvider
from app.api.routes import router
from app.core.config import Settings
from app.core.errors import AppError
from app.core.http import LocalHTTPBoundary, error_response
from app.domain.models import ErrorEnvelope
from app.services.conversation import ConversationService
from app.settings.manager import DynamicProvider, LocalSettings
from app.settings.routes import router as settings_router


def create_app(
    settings: Settings | None = None,
    provider: ChatProvider | None = None,
    local_admin: LocalSettings | None = None,
) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        selected = (
            provider
            or (DynamicProvider(local_admin) if local_admin else None)
            or (MockProvider() if settings.llm_provider == "mock" else OpenAIProvider(settings))
        )
        application.state.conversation = ConversationService(
            local_admin.initial if local_admin else settings, selected
        )
        try:
            yield
        finally:
            await selected.aclose()

    application = FastAPI(
        title="Desktop-NOMI backend",
        version="0.2.0",
        lifespan=lifespan,
        responses={
            status: {"model": ErrorEnvelope}
            for status in (403, 404, 409, 413, 415, 422, 500, 502, 503, 504)
        },
    )
    application.state.settings = local_admin.initial if local_admin else settings
    application.state.local_admin = local_admin
    application.include_router(router)
    application.include_router(settings_router)

    @application.exception_handler(AppError)
    async def handle_app_error(request: Request, error: AppError):
        return error_response(error, request.state.request_id)

    @application.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, error: RequestValidationError):
        # FastAPI's default details can echo private input; return a fixed message.
        return error_response(
            AppError(422, "VALIDATION_ERROR", "请求字段、类型或长度不合法。"),
            request.state.request_id,
        )

    @application.exception_handler(HTTPException)
    async def handle_http_error(request: Request, error: HTTPException):
        return error_response(
            AppError(error.status_code, "HTTP_ERROR", "请求路径或方法不可用。"),
            request.state.request_id,
        )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Request-ID"],
    )
    application.add_middleware(LocalHTTPBoundary, settings=settings, local_admin=local_admin)
    return application


app = create_app()
