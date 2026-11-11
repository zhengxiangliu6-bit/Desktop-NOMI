import asyncio
import hashlib
import ipaddress
import secrets
import time
from collections.abc import Callable

from pydantic import ValidationError

from app.adapters.llm.mock import MockProvider
from app.adapters.llm.openai import OpenAIProvider
from app.core.config import Settings
from app.core.errors import AppError, ModelFormatError, ProviderTimeoutError, missing_configuration
from app.domain.models import SYSTEM_PROMPT, ChatMessage, StructuredReply
from app.settings.models import BAILIAN_ROOTS, Profile, ProfileUpdate
from app.settings.network import secure_client
from app.settings.vault import Vault, VaultError


def denied() -> AppError:
    return AppError(403, "SETTINGS_FORBIDDEN", "配置操作未授权，请从本机终端启用并重新配对。")


def default_factory(settings: Settings, managed: bool):
    if settings.llm_provider == "mock":
        return MockProvider()
    if not settings.openai_configured:
        raise missing_configuration()
    return OpenAIProvider(
        settings, secure_client(settings.llm_timeout_seconds) if managed else None
    )


class LocalSettings:
    def __init__(
        self,
        settings: Settings,
        vault: Vault,
        pairing_code: str | None,
        factory=default_factory,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.initial = settings.model_copy(update={"llm_api_key": None})
        self.vault = vault
        self.factory = factory
        self.clock = clock
        self.created = clock()
        self.enabled = pairing_code is not None
        self.pair_digest = hashlib.sha256((pairing_code or "").encode()).digest()
        self.attempts = 0
        self.token_digest: bytes | None = None
        self.expires = 0.0
        self.revision = 0
        self.tested = False
        self.testing = False
        stored = vault.load()
        if stored and (
            not stored.managed or (stored.base_url and stored.base_url not in BAILIAN_ROOTS)
        ):
            raise VaultError("Saved profile rejected")
        self.profile = stored or Profile(
            provider=settings.llm_provider,
            base_url=settings.llm_base_url or "",
            model=settings.llm_model or "",
            api_key=settings.llm_api_key,
            max_tokens=settings.llm_max_output_tokens,
            token_parameter=settings.llm_token_parameter,
            json_mode=settings.llm_json_mode,
        )

    def boundary(self, scope, headers, path):
        try:
            local = ipaddress.ip_address(scope["client"][0]).is_loopback
        except (ValueError, TypeError, KeyError):
            local = False
        raw = scope.get("headers", [])
        unique = all(sum(key == name for key, _ in raw) == 1 for name in (b"host", b"origin"))
        if (
            not local
            or not unique
            or headers.get("origin") not in {"http://localhost:5173", "http://127.0.0.1:5173"}
            or headers.get("origin") not in self.initial.allowed_origins
            or headers.get("sec-fetch-site", "same-origin") != "same-origin"
        ):
            raise denied()
        if path == "/api/v0/settings/pair":
            return
        authorization = headers.get("authorization", "")
        if (
            sum(key == b"authorization" for key, _ in raw) != 1
            or not authorization.startswith("Bearer ")
            or not self.token_digest
            or self.clock() >= self.expires
            or not secrets.compare_digest(
                hashlib.sha256(authorization[7:].encode()).digest(), self.token_digest
            )
        ):
            raise denied()

    def pair(self, code: str) -> str:
        if not self.enabled:
            raise denied()
        self.attempts += 1
        if self.attempts > 5 or self.token_digest or self.clock() - self.created > 300:
            raise denied()
        if not secrets.compare_digest(hashlib.sha256(code.encode()).digest(), self.pair_digest):
            raise denied()
        token = secrets.token_urlsafe(32)
        self.token_digest = hashlib.sha256(token.encode()).digest()
        self.expires = self.clock() + 1800
        return token

    def settings(self, profile: Profile | None = None) -> Settings:
        profile = profile or self.profile
        return self.initial.model_copy(
            update={
                "llm_provider": profile.provider,
                "llm_base_url": profile.base_url or None,
                "llm_model": profile.model or None,
                "llm_api_key": profile.api_key,
                "llm_max_output_tokens": profile.max_tokens,
                "llm_token_parameter": profile.token_parameter,
                "llm_json_mode": profile.json_mode,
            }
        )

    def public(self):
        value = self.profile
        return {
            "provider": value.provider,
            "base_url": value.base_url,
            "model": value.model,
            "key_configured": bool(value.api_key and value.api_key.get_secret_value()),
            "max_tokens": value.max_tokens,
            "token_parameter": value.token_parameter,
            "json_mode": value.json_mode,
            "storage": self.vault.kind,
            "revision": self.revision,
            "connection": "verified" if self.tested else "not_tested",
            "allowed_base_urls": list(BAILIAN_ROOTS),
        }

    def update(self, change: ProfileUpdate, conversation):
        if self.testing or any(session.busy for session in conversation.sessions.values()):
            raise AppError(409, "CONFIGURATION_BUSY", "请等待当前请求完成后再修改配置。")
        if change.provider == "openai" and (not change.base_url or not change.model):
            raise AppError(422, "VALIDATION_ERROR", "请选择受支持的 Base URL 并填写模型 ID。")
        key = self.profile.api_key
        if change.key_action == "keep" and change.api_key is not None:
            raise AppError(422, "VALIDATION_ERROR", "更新 Key 时必须选择替换。")
        if key and change.base_url != self.profile.base_url and change.key_action == "keep":
            raise AppError(409, "KEY_SCOPE_CHANGED", "更换 API 入口时请明确替换或清除 Key。")
        if change.key_action == "replace":
            if not change.api_key:
                raise AppError(422, "VALIDATION_ERROR", "替换 Key 时请输入新凭据。")
            key = change.api_key
        if change.key_action == "clear":
            if change.api_key is not None:
                raise AppError(422, "VALIDATION_ERROR", "清除 Key 时不要提交新凭据。")
            key = None
        profile = Profile(
            provider=change.provider,
            base_url=change.base_url,
            model=change.model,
            api_key=key,
            max_tokens=change.max_tokens,
            token_parameter=change.token_parameter,
            json_mode=change.json_mode,
            managed=True,
        )
        try:
            self.vault.save(profile)
        except Exception:
            raise AppError(
                503, "CREDENTIAL_STORAGE_ERROR", "系统凭据保存失败，配置未更改。"
            ) from None
        self.profile = profile
        self.revision += 1
        self.tested = False
        conversation.sessions.clear()
        return self.public()

    async def test_connection(self, revision: int):
        if self.testing or revision != self.revision:
            raise AppError(409, "CONFIGURATION_BUSY", "配置已变化或连接测试正在运行，请重新读取。")
        profile = self.profile
        self.testing = True
        self.tested = False
        provider = None
        try:
            if profile.provider == "openai" and (
                not profile.managed or profile.base_url not in BAILIAN_ROOTS
            ):
                raise AppError(422, "VALIDATION_ERROR", "请先保存受支持的百炼入口配置。")
            settings = self.settings(profile)
            if not settings.chat_available:
                raise AppError(503, "CONFIGURATION_MISSING", "配置尚不完整。")
            settings = settings.model_copy(
                update={"llm_max_output_tokens": min(settings.llm_max_output_tokens, 256)}
            )
            provider = self.factory(settings, profile.managed)
            async with asyncio.timeout(settings.llm_timeout_seconds):
                raw = await provider.complete(
                    [
                        ChatMessage("system", SYSTEM_PROMPT),
                        ChatMessage("user", "Connection test. Return a short valid JSON greeting."),
                    ]
                )
            try:
                StructuredReply.model_validate_json(raw)
            except (ValidationError, TypeError):
                raise ModelFormatError() from None
            self.tested = True
            # Do not return provider text: even a malicious echo cannot disclose a credential.
            return {"ok": True, "provider": profile.provider, "revision": self.revision}
        except TimeoutError:
            raise ProviderTimeoutError() from None
        finally:
            self.testing = False
            if provider:
                await provider.aclose()


class DynamicProvider:
    def __init__(self, manager: LocalSettings):
        self.manager = manager

    @property
    def name(self):
        return self.manager.profile.provider

    async def complete(self, messages):
        profile = self.manager.profile
        provider = self.manager.factory(self.manager.settings(profile), profile.managed)
        try:
            return await provider.complete(messages)
        finally:
            await provider.aclose()

    async def aclose(self):
        pass
