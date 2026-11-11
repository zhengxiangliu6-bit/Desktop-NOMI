import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.adapters.llm.openai import MAX_UPSTREAM_BYTES, OpenAIProvider
from app.core.errors import ModelFormatError, ProviderRequestError, ProviderTimeoutError
from app.domain.models import ChatMessage
from app.main import create_app
from tests.helpers import reply_json


def real_settings(settings_factory, **changes):
    return settings_factory(
        llm_provider="openai",
        llm_base_url="https://provider.example/v1/",
        llm_model="test-model-configured",
        llm_api_key="test-placeholder-not-real",
        **changes,
    )


def envelope(content=None, **changes):
    return {
        "choices": [
            {"message": {"content": content or reply_json()}, "finish_reason": "stop", **changes}
        ]
    }


@pytest.mark.parametrize("json_mode", [False, True])
async def test_configured_request_and_no_implicit_v1_or_tool_execution(settings_factory, json_mode):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=envelope())

    settings = real_settings(settings_factory, llm_json_mode=json_mode)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAIProvider(settings, client)
        raw = await provider.complete(
            [ChatMessage("system", "protocol"), ChatMessage("user", "hello")]
        )
    assert json.loads(raw)["reply"] == "测试回复"
    assert len(requests) == 1
    assert str(requests[0].url) == "https://provider.example/v1/chat/completions"
    assert requests[0].headers["Authorization"] == "Bearer test-placeholder-not-real"
    payload = json.loads(requests[0].content)
    assert payload["model"] == "test-model-configured"
    assert payload["stream"] is False
    assert payload["messages"][1] == {"role": "user", "content": "hello"}
    assert ("response_format" in payload) is json_mode
    assert "tools" not in payload and "functions" not in payload


@pytest.mark.parametrize("status", [301, 400, 401, 403, 429, 500])
async def test_http_errors_are_sanitized_not_retried_or_redirected(settings_factory, status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status,
            text="provider-private-error-and-test-placeholder-not-real",
            headers={"Location": "https://other.example/collect"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAIProvider(real_settings(settings_factory), client)
        with pytest.raises(ProviderRequestError) as error:
            await provider.complete([ChatMessage("user", "hello")])
        assert "private" not in str(error.value)
        assert len(calls) == 1


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (httpx.ReadTimeout("private-timeout-details"), ProviderTimeoutError),
        (httpx.ConnectTimeout("private-connect-details"), ProviderTimeoutError),
        (httpx.ConnectError("private-request-details"), ProviderRequestError),
    ],
)
async def test_transport_errors_are_distinct(settings_factory, exception, expected):
    def handler(request):
        raise exception

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(expected):
            await OpenAIProvider(real_settings(settings_factory), client).complete(
                [ChatMessage("user", "hi")]
            )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="invalid-json"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": [{"message": {"content": None}}]}),
        httpx.Response(200, json=envelope(finish_reason="length")),
        httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": reply_json(), "tool_calls": [{"name": "shell"}]}}
                ]
            },
        ),
        httpx.Response(200, content=b"x" * (MAX_UPSTREAM_BYTES + 1)),
    ],
)
async def test_bad_envelopes_and_oversized_responses(settings_factory, response):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response)) as client:
        with pytest.raises(ModelFormatError):
            await OpenAIProvider(real_settings(settings_factory), client).complete(
                [ChatMessage("user", "hi")]
            )


def test_fastapi_real_provider_path_uses_mock_transport_only(settings_factory):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=envelope(reply_json(reply="真实适配路径，假 HTTP 响应")))

    provider = OpenAIProvider(
        real_settings(settings_factory), httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    with TestClient(
        create_app(real_settings(settings_factory), provider), base_url="http://localhost"
    ) as client:
        response = client.post("/api/v0/chat", json={"text": "hello"})
        assert response.status_code == 200
        assert response.json()["provider"] == "openai"
        assert response.json()["motion"] == "nod"
        assert len(requests) == 1
        assert "test-placeholder-not-real" not in response.text


def test_api_transport_timeout_then_recovery_keeps_good_context(settings_factory):
    requests = []

    def handler(request):
        requests.append(request)
        if len(requests) == 2:
            raise httpx.ReadTimeout("private network details")
        return httpx.Response(200, json=envelope())

    settings = real_settings(settings_factory)
    provider = OpenAIProvider(settings, httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    with TestClient(create_app(settings, provider), base_url="http://localhost") as client:
        first = client.post("/api/v0/chat", json={"text": "first"}).json()
        session_id = first["session_id"]
        failed = client.post("/api/v0/chat", json={"text": "failed-turn", "session_id": session_id})
        assert failed.status_code == 504
        assert failed.json()["error"]["code"] == "UPSTREAM_TIMEOUT"
        recovered = client.post(
            "/api/v0/chat", json={"text": "retry-manually", "session_id": session_id}
        )
        assert recovered.status_code == 200
        context = json.loads(requests[-1].content)["messages"]
        assert [item["role"] for item in context] == ["system", "user", "assistant", "user"]
        assert "failed-turn" not in [item["content"] for item in context]
        assert "private network details" not in failed.text
