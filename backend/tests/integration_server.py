"""Test-only ASGI entrypoint. No extra routes, real credentials or paid Provider."""

import asyncio

from app.adapters.llm.mock import MockProvider
from app.core.config import Settings
from app.core.errors import ModelFormatError, ProviderRequestError, ProviderTimeoutError
from app.main import create_app
from app.settings.manager import LocalSettings
from app.settings.vault import MemoryVault


class IntegrationMockProvider(MockProvider):
    async def complete(self, messages):
        await asyncio.sleep(0.3)
        text = messages[-1].content
        if text == "test:timeout":
            raise ProviderTimeoutError()
        if text == "test:upstream":
            raise ProviderRequestError()
        if text == "test:format":
            raise ModelFormatError()
        if text == "test:slow":
            await asyncio.sleep(1)
        return await super().complete(messages)


settings = Settings(_env_file=None, llm_provider="mock", session_ttl_seconds=4)


def test_factory(current, managed):
    provider = IntegrationMockProvider()
    provider.name = current.llm_provider
    return provider


app = create_app(
    settings,
    local_admin=LocalSettings(
        settings, MemoryVault(), "fixture-local-pairing-code", factory=test_factory
    ),
)
