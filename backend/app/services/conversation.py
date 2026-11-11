import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.adapters.llm.base import ChatProvider
from app.core.config import Settings
from app.core.errors import AppError, ModelFormatError, ProviderTimeoutError
from app.domain.models import SYSTEM_PROMPT, ChatMessage, ChatRequest, ChatResponse, StructuredReply

Turn = tuple[ChatMessage, ChatMessage]


def recent_turns(turns: list[Turn], *, count: int, chars: int) -> list[Turn]:
    """Newest contiguous suffix, preserving whole user/assistant pairs."""
    selected: list[Turn] = []
    for turn in reversed(turns):
        size = sum(len(message.content) for message in turn)
        if len(selected) >= count or size > chars:
            break
        selected.append(turn)
        chars -= size
    return list(reversed(selected))


@dataclass
class Session:
    last_used: float
    turns: list[Turn] = field(default_factory=list)
    busy: bool = False


class ConversationService:
    """Single-process/event-loop memory context; no file, shell or device access."""

    def __init__(
        self,
        settings: Settings,
        provider: ChatProvider,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.settings = settings
        self.provider = provider
        self.clock = clock
        self.sessions: dict[UUID, Session] = {}

    def reserve(self, session_id: UUID | None) -> tuple[UUID, Session, bool]:
        now = self.clock()
        for key, session in list(self.sessions.items()):
            if not session.busy and now - session.last_used >= self.settings.session_ttl_seconds:
                del self.sessions[key]
        is_new = session_id is None
        if is_new:
            if len(self.sessions) >= self.settings.max_sessions:
                raise AppError(503, "SESSION_LIMIT_REACHED", "会话容量已满，请稍后重试。", True)
            session_id = uuid4()
            self.sessions[session_id] = Session(last_used=now)
        session = self.sessions.get(session_id)
        if session is None:
            raise AppError(404, "SESSION_NOT_FOUND", "会话不存在、已过期或服务已重启。")
        if session.busy:
            raise AppError(409, "SESSION_BUSY", "该会话正在处理另一条消息。", True)
        # No await between checking and reserving: atomic on the app's event loop.
        session.busy = True
        return session_id, session, is_new

    async def chat(self, request: ChatRequest) -> ChatResponse:
        session_id, session, is_new = self.reserve(request.session_id)
        success = False
        try:
            user = ChatMessage("user", request.text)
            history = recent_turns(
                session.turns,
                count=self.settings.context_max_turns - 1,
                chars=self.settings.context_max_chars - len(SYSTEM_PROMPT) - len(user.content),
            )
            messages = [ChatMessage("system", SYSTEM_PROMPT)]
            messages.extend(message for turn in history for message in turn)
            messages.append(user)
            try:
                async with asyncio.timeout(self.settings.llm_timeout_seconds):
                    raw = await self.provider.complete(messages)
            except TimeoutError:
                raise ProviderTimeoutError() from None
            try:
                parsed = StructuredReply.model_validate_json(raw)
            except (ValidationError, TypeError):
                raise ModelFormatError() from None
            assistant = ChatMessage("assistant", parsed.model_dump_json())
            retained = recent_turns(
                [*history, (user, assistant)],
                count=self.settings.context_max_turns,
                chars=self.settings.context_max_chars - len(SYSTEM_PROMPT),
            )
            response = ChatResponse(
                **parsed.model_dump(),
                session_id=session_id,
                provider=self.provider.name,
            )
            session.turns = retained
            success = True
            return response
        finally:
            session.busy = False
            session.last_used = self.clock()
            if is_new and not success:
                # Failed anonymous requests must not consume unreturnable session IDs.
                self.sessions.pop(session_id, None)
