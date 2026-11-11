from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.errors import ProviderRequestError, ProviderTimeoutError
from app.main import create_app
from tests.helpers import ScriptedProvider, reply_json


def test_mock_health_chat_and_openapi_without_credentials(settings_factory):
    app = create_app(settings_factory())
    with TestClient(app, base_url="http://localhost") as client:
        health = client.get("/api/v0/health")
        assert health.json() == {
            "status": "ok",
            "api_version": "v0",
            "provider": "mock",
            "capabilities": {"chat": True, "stt": False, "tts": False, "device": False},
        }
        response = client.post("/api/v0/chat", json={"text": "  你好  "})
        assert response.status_code == 200
        body = response.json()
        UUID(body["session_id"])
        assert body["provider"] == "mock"
        assert body["reply"].startswith("[Mock]")
        assert body["emotion"] == "happy"
        assert body["motion"] == "nod"
        again = client.post(
            "/api/v0/chat", json={"text": "今天有点累", "session_id": body["session_id"]}
        )
        assert again.json()["session_id"] == body["session_id"]
        assert again.json()["emotion"] == "concerned"
        assert len(app.state.conversation.sessions[UUID(body["session_id"])].turns) == 2
        assert response.headers["x-request-id"]
        assert response.headers["cache-control"] == "no-store"
        schema = client.get("/openapi.json").json()
        assert "/api/v0/chat" in schema["paths"]
        assert schema["components"]["schemas"]["Motion"]["enum"] == [
            "none",
            "nod",
            "tilt",
            "bounce",
        ]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"text": ""},
        {"text": "   "},
        {"text": "a" * 4001},
        {"text": 123},
        {"text": None},
        {"text": ["hello"]},
        {"text": "hello", "session_id": "bad"},
        {"text": "hello", "role": "system"},
        {"text": "hello", "motion": "shell"},
    ],
)
def test_invalid_input_does_not_call_provider(settings_factory, payload):
    provider = ScriptedProvider()
    with TestClient(
        create_app(settings_factory(), provider), base_url="http://localhost"
    ) as client:
        response = client.post("/api/v0/chat", json=payload)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
        assert provider.calls == []


@pytest.mark.parametrize(
    ("failure", "status", "code"),
    [
        (ProviderRequestError(), 502, "UPSTREAM_ERROR"),
        (ProviderTimeoutError(), 504, "UPSTREAM_TIMEOUT"),
        ("not-json", 502, "UPSTREAM_INVALID_RESPONSE"),
        (RuntimeError("private-provider-data"), 500, "INTERNAL_ERROR"),
    ],
)
def test_error_categories_and_recovery(settings_factory, failure, status, code):
    provider = ScriptedProvider(reply_json(), failure, reply_json(reply="恢复成功"))
    app = create_app(settings_factory(), provider)
    with TestClient(app, base_url="http://localhost") as client:
        session_id = client.post("/api/v0/chat", json={"text": "第一轮"}).json()["session_id"]
        error = client.post("/api/v0/chat", json={"text": "失败的输入", "session_id": session_id})
        assert error.status_code == status
        assert error.json()["error"]["code"] == code
        assert "private-provider-data" not in error.text
        assert "失败的输入" not in error.text
        recovered = client.post("/api/v0/chat", json={"text": "继续", "session_id": session_id})
        assert recovered.status_code == 200
        assert recovered.json()["reply"] == "恢复成功"
        assert "失败的输入" not in [item.content for item in provider.calls[-1]]
    assert provider.closed


def test_unknown_session_and_missing_real_configuration(settings_factory):
    with TestClient(create_app(settings_factory()), base_url="http://localhost") as client:
        response = client.post("/api/v0/chat", json={"text": "你好", "session_id": str(uuid4())})
        assert response.status_code == 404
    app = create_app(settings_factory(llm_provider="openai"))
    with TestClient(app, base_url="http://localhost") as client:
        assert client.get("/api/v0/health").json()["capabilities"]["chat"] is False
        response = client.post("/api/v0/chat", json={"text": "你好"})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "CONFIGURATION_MISSING"
        assert app.state.conversation.sessions == {}


def test_http_security_body_limit_and_safe_logging(settings_factory, caplog):
    with TestClient(create_app(settings_factory()), base_url="http://localhost") as client:
        assert client.get("/api/v0/health", headers={"Host": "evil.example"}).status_code == 403
        assert client.get("/api/v0/health", headers={"Host": "evil@localhost"}).status_code == 403
        assert (
            client.get("/api/v0/health", headers={"Origin": "https://evil.example"}).status_code
            == 403
        )
        assert client.post("/api/v0/chat", content="text").status_code == 415
        oversized = client.post(
            "/api/v0/chat", content=b"x" * 65537, headers={"Content-Type": "application/json"}
        )
        assert oversized.status_code == 413
        invalid = client.post(
            "/api/v0/chat", content="{", headers={"Content-Type": "application/json"}
        )
        assert invalid.status_code == 422
        allowed = client.get("/api/v0/health", headers={"Origin": "http://localhost:5173"})
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "access-control-allow-credentials" not in allowed.headers
        assert client.get("/api/v0/absent").status_code == 404
        with caplog.at_level("INFO", logger="nomi.requests"):
            response = client.post("/api/v0/chat", json={"text": "private-fictional-chat"})
        assert response.status_code == 200
        assert "request_id=" in caplog.text
        assert "private-fictional-chat" not in caplog.text


async def test_streamed_body_limit_without_content_length(settings_factory):
    import httpx

    provider = ScriptedProvider()
    app = create_app(settings_factory(), provider)

    async def chunks():
        yield b"x" * 40000
        yield b"x" * 40000

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://localhost"
        ) as client:
            response = await client.post(
                "/api/v0/chat", content=chunks(), headers={"Content-Type": "application/json"}
            )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert provider.calls == []
