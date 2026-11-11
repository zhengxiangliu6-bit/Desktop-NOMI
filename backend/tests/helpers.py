import json

from app.domain.models import ChatMessage


def reply_json(**changes) -> str:
    return json.dumps({"reply": "测试回复", "emotion": "happy", "motion": "nod", **changes})


class ScriptedProvider:
    name = "mock"

    def __init__(self, *results: str | Exception):
        self.results = list(results)
        self.calls: list[list[ChatMessage]] = []
        self.closed = False

    async def complete(self, messages: list[ChatMessage]) -> str:
        self.calls.append(list(messages))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def aclose(self) -> None:
        self.closed = True
