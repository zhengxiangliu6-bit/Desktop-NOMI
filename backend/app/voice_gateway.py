"""Dedicated device gateway. Run separately from the browser/chat application."""
import hmac
import io
import os
import re
import wave

import httpx
from fastapi import FastAPI, HTTPException, Request

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
COMMANDS = {
    "开心一点": "happy", "难过一点": "sad", "眨一下眼": "blink",
    "好奇一点": "curious", "思考一下": "thinking", "认真听讲": "listening",
    "说话表情": "speaking", "回到待机": "idle", "休息一下": "idle",
    "生气一下": "angry", "惊讶一下": "surprised", "困倦一下": "sleepy",
    "单眼眨眼": "wink", "喜欢表情": "love", "疑惑一下": "confused",
}
MAX_BYTES = 16000 * 2 * 4


def action_for(transcript: str) -> str | None:
    words = re.sub(r"[\s，。！？,.!?、]+", "", transcript)
    for prefix in ("你好小米同学", "小米同学"):
        if words.startswith(prefix):
            words = words[len(prefix):]
            break
    return COMMANDS.get(words)


@app.post("/device/voice")
async def voice(request: Request):
    token = os.getenv("NOMI_DEVICE_TOKEN", "")
    key = os.getenv("NOMI_ASR_API_KEY", "")
    auth = request.headers.get("authorization", "").encode()
    if len(token) < 24 or not key:
        raise HTTPException(503, "Voice gateway is not configured")
    if not hmac.compare_digest(auth, f"Bearer {token}".encode()):
        raise HTTPException(401, "Unauthorized")
    if request.headers.get("content-type") != "application/octet-stream":
        raise HTTPException(415, "Expected PCM16LE mono at 16 kHz")
    pcm = bytearray()
    async for chunk in request.stream():
        if len(pcm) + len(chunk) > MAX_BYTES:
            raise HTTPException(413, "Audio exceeds four seconds")
        pcm.extend(chunk)
    if len(pcm) < 3200 or len(pcm) % 2:
        raise HTTPException(422, "Invalid PCM length")
    wav = io.BytesIO()
    with wave.open(wav, "wb") as out:
        out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        out.writeframes(pcm)
    url = os.getenv("NOMI_ASR_URL", "https://api.openai.com/v1/audio/transcriptions")
    if not url.startswith("https://"):
        raise HTTPException(503, "ASR requires HTTPS")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers={"Authorization": f"Bearer {key}"},
                files={"file": ("speech.wav", wav.getvalue(), "audio/wav")},
                data={"model": os.getenv("NOMI_ASR_MODEL", "gpt-4o-mini-transcribe"),
                      "language": "zh"})
            response.raise_for_status()
            transcript = response.json()["text"]
            if not isinstance(transcript, str):
                raise ValueError("Invalid transcript")
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(502, "Speech provider failed") from None
    return {"text": transcript[:180], "action": action_for(transcript)}
