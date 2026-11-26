import io
import wave
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.voice_gateway import action_for, app


def test_rules():
    assert action_for("你好，小米同学，开心一点。") == "happy"
    assert action_for("小米同学") is None
    assert action_for("不要开心一点") is None


def test_authenticated_pcm_to_transcript(monkeypatch):
    token = "test-device-token-at-least-24"
    monkeypatch.setenv("NOMI_DEVICE_TOKEN", token)
    monkeypatch.setenv("NOMI_ASR_API_KEY", "fixture-key")
    request_headers = {"Authorization": "Bearer " + token,
                       "Content-Type": "application/octet-stream"}
    pcm = bytes(3200)
    client = TestClient(app)
    assert client.post("/device/voice", content=pcm).status_code == 401
    assert client.post("/device/voice", headers=request_headers,
                       content=bytes(128001)).status_code == 413
    original = httpx.AsyncClient

    def provider(request):
        assert request.headers["authorization"] == "Bearer fixture-key"
        content = request.read()
        start = content.index(b"RIFF")
        with wave.open(io.BytesIO(content[start:]), "rb") as audio:
            assert (audio.getframerate(), audio.getnchannels()) == (16000, 1)
            assert audio.readframes(1600) == pcm
        return httpx.Response(200, json={"text": "小米同学，开心一点。"})

    with patch("app.voice_gateway.httpx.AsyncClient",
               side_effect=lambda **kw: original(transport=httpx.MockTransport(provider), **kw)):
        response = client.post("/device/voice", headers=request_headers, content=pcm)
    assert response.status_code == 200
    assert response.json() == {"text": "小米同学，开心一点。", "action": "happy"}
