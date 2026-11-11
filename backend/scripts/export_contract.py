"""Refresh the cross-language snapshot from the implemented Pydantic models."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.domain.models import ChatRequest, ChatResponse  # noqa: E402

snapshot = {
    "request": ChatRequest.model_json_schema(),
    "response": ChatResponse.model_json_schema(),
}
path = Path(__file__).resolve().parents[2] / "contracts/chat-v0.json"
path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
