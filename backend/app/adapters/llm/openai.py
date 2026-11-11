import json

import httpx

from app.core.config import Settings
from app.core.errors import (
    ModelFormatError,
    ProviderRequestError,
    ProviderTimeoutError,
    missing_configuration,
)
from app.domain.models import ChatMessage

MAX_UPSTREAM_BYTES = 128 * 1024


class OpenAIProvider:
    name = "openai"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient(
            timeout=settings.llm_timeout_seconds,
            follow_redirects=False,
        )

    async def complete(self, messages: list[ChatMessage]) -> str:
        settings = self.settings
        if not settings.openai_configured:
            raise missing_configuration()
        payload = {
            "model": settings.llm_model,
            "messages": [{"role": item.role, "content": item.content} for item in messages],
            "stream": False,
            settings.llm_token_parameter: settings.llm_max_output_tokens,
        }
        if settings.llm_json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            # No redirect following or automatic retries: never forward keys elsewhere.
            async with self.client.stream(
                "POST",
                f"{settings.llm_base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {settings.llm_api_key.get_secret_value()}"},
                follow_redirects=False,
            ) as response:
                if not 200 <= response.status_code < 300:
                    raise ProviderRequestError()
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    body.extend(chunk)
                    if len(body) > MAX_UPSTREAM_BYTES:
                        raise ModelFormatError()
        except httpx.TimeoutException:
            raise ProviderTimeoutError() from None
        except (httpx.RequestError, httpx.InvalidURL):
            raise ProviderRequestError() from None
        try:
            envelope = json.loads(body)
            choice = envelope["choices"][0]
            message = choice["message"]
            content = message["content"]
            if (
                not isinstance(content, str)
                or not content.strip()
                or message.get("tool_calls")
                or message.get("function_call")
                or choice.get("finish_reason") not in {None, "stop"}
            ):
                raise ModelFormatError()
            if settings.llm_api_key.get_secret_value() in content:
                raise ModelFormatError()
            return content
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise ModelFormatError() from None

    async def aclose(self) -> None:
        await self.client.aclose()
