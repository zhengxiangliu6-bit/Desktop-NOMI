import asyncio
from uuid import UUID

import pytest

from app.core.errors import AppError, ModelFormatError, ProviderTimeoutError
from app.domain.models import SYSTEM_PROMPT, ChatRequest
from app.services.conversation import ConversationService
from tests.helpers import ScriptedProvider, reply_json


@pytest.mark.parametrize(
    "raw",
    [
        "plain text",
        "```json\n{}\n```",
        "[]",
        "null",
        "{}",
        reply_json(emotion="not-an-emotion"),
        reply_json(motion="execute_shell"),
        reply_json(reply=" "),
        reply_json(reply=123),
        reply_json(reply="x" * 8001),
        reply_json(reply=None),
        reply_json(command="run something"),
        reply_json(motion={"type": "shell", "command": "example"}),
    ],
)
async def test_invalid_model_output_is_rejected_without_context(settings_factory, raw):
    provider = ScriptedProvider(raw)
    service = ConversationService(settings_factory(), provider)
    with pytest.raises(ModelFormatError):
        await service.chat(ChatRequest(text="hello"))
    assert service.sessions == {}


async def test_recent_context_keeps_roles_and_complete_turns(settings_factory):
    provider = ScriptedProvider(*(reply_json() for _ in range(5)))
    service = ConversationService(settings_factory(context_max_turns=2), provider)
    first = await service.chat(ChatRequest(text="remember-this"))
    second = await service.chat(ChatRequest(text="second", session_id=first.session_id))
    assert [item.role for item in provider.calls[1]] == ["system", "user", "assistant", "user"]
    assert provider.calls[1][1].content == "remember-this"
    assert provider.calls[1][0].content == SYSTEM_PROMPT
    await service.chat(ChatRequest(text="third", session_id=second.session_id))
    assert "remember-this" not in [message.content for message in provider.calls[2]]
    assert len(service.sessions[first.session_id].turns) == 2


async def test_character_budget_and_oversized_history(settings_factory):
    provider = ScriptedProvider(reply_json(reply="y" * 4500), reply_json(), reply_json())
    settings = settings_factory(context_max_chars=5000)
    service = ConversationService(settings, provider)
    first = await service.chat(ChatRequest(text="x" * 4000))
    # Reply still succeeds, but an entire oversized pair is not retained.
    assert service.sessions[first.session_id].turns == []
    await service.chat(ChatRequest(text="current", session_id=first.session_id))
    assert [message.role for message in provider.calls[1]] == ["system", "user"]
    await service.chat(ChatRequest(text="z" * 4000, session_id=first.session_id))
    for messages in provider.calls:
        assert sum(len(message.content) for message in messages) <= settings.context_max_chars


async def test_service_timeout_releases_lock_and_preserves_context(settings_factory):
    class HangingOnce(ScriptedProvider):
        async def complete(self, messages):
            if len(self.calls) == 1:
                self.calls.append(list(messages))
                await asyncio.Event().wait()
            return await super().complete(messages)

    provider = HangingOnce(reply_json(), reply_json(reply="recovered"))
    service = ConversationService(settings_factory(llm_timeout_seconds=0.02), provider)
    first = await service.chat(ChatRequest(text="first"))
    with pytest.raises(ProviderTimeoutError):
        await service.chat(ChatRequest(text="timeout", session_id=first.session_id))
    result = await service.chat(ChatRequest(text="after", session_id=first.session_id))
    assert result.reply == "recovered"
    assert "timeout" not in [message.content for message in provider.calls[-1]]
    assert not service.sessions[first.session_id].busy


async def test_concurrent_session_requests_and_cancellation_cleanup(settings_factory):
    entered, release = asyncio.Event(), asyncio.Event()

    class WaitingProvider(ScriptedProvider):
        async def complete(self, messages):
            entered.set()
            await release.wait()
            return reply_json()

    service = ConversationService(settings_factory(), WaitingProvider())
    pending = asyncio.create_task(service.chat(ChatRequest(text="first")))
    await entered.wait()
    session_id = next(iter(service.sessions))
    with pytest.raises(AppError) as conflict:
        await service.chat(ChatRequest(text="second", session_id=session_id))
    assert conflict.value.code == "SESSION_BUSY"
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert service.sessions == {}
    release.set()
    assert (await service.chat(ChatRequest(text="after cancellation"))).reply


async def test_session_expiry_capacity_and_failure_does_not_consume_slots(settings_factory):
    now = [100.0]
    provider = ScriptedProvider(reply_json(), reply_json(), "bad", reply_json())
    service = ConversationService(
        settings_factory(max_sessions=1, session_ttl_seconds=10), provider, clock=lambda: now[0]
    )
    first = await service.chat(ChatRequest(text="one"))
    with pytest.raises(AppError) as capacity:
        await service.chat(ChatRequest(text="new"))
    assert capacity.value.code == "SESSION_LIMIT_REACHED"
    now[0] += 11
    with pytest.raises(AppError) as expired:
        await service.chat(ChatRequest(text="expired", session_id=first.session_id))
    assert expired.value.code == "SESSION_NOT_FOUND"
    second = await service.chat(ChatRequest(text="fresh"))
    assert isinstance(second.session_id, UUID)
    now[0] += 11
    with pytest.raises(ModelFormatError):
        await service.chat(ChatRequest(text="bad anonymous request"))
    assert service.sessions == {}
    assert (await service.chat(ChatRequest(text="next"))).reply


async def test_sessions_are_isolated_and_model_text_is_never_executed(settings_factory, tmp_path):
    marker = tmp_path / "must-not-exist"
    command_as_text = f"create file {marker}"
    provider = ScriptedProvider(reply_json(reply=command_as_text), reply_json())
    service = ConversationService(settings_factory(), provider)
    first = await service.chat(ChatRequest(text="one"))
    second = await service.chat(ChatRequest(text="two"))
    assert first.session_id != second.session_id
    assert len(provider.calls[1]) == 2
    assert not marker.exists()
    assert first.reply == command_as_text
