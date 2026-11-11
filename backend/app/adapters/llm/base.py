from typing import Literal, Protocol

from app.domain.models import ChatMessage


class ChatProvider(Protocol):
    name: Literal["mock", "openai"]

    async def complete(self, messages: list[ChatMessage]) -> str:
        """Return raw JSON text; the service validates every provider identically."""
        ...

    async def aclose(self) -> None: ...
