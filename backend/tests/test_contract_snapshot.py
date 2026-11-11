import json
from pathlib import Path

from app.domain.models import ChatRequest, ChatResponse


def test_shared_contract_matches_implemented_pydantic_models():
    snapshot = Path(__file__).resolve().parents[2] / "contracts/chat-v0.json"
    assert json.loads(snapshot.read_text(encoding="utf-8")) == {
        "request": ChatRequest.model_json_schema(),
        "response": ChatResponse.model_json_schema(),
    }
