from app.domain.models import ChatMessage, Emotion, Motion, StructuredReply


class MockProvider:
    name = "mock"

    async def complete(self, messages: list[ChatMessage]) -> str:
        text = messages[-1].content
        if "累" in text or "难过" in text:
            reply = StructuredReply(
                reply="[Mock] 慢慢来，今天也可以休息一下。",
                emotion=Emotion.CONCERNED,
                motion=Motion.TILT,
            )
        else:
            reply = StructuredReply(
                reply="[Mock] 我收到你的消息了，很高兴陪着你。",
                emotion=Emotion.HAPPY,
                motion=Motion.NOD,
            )
        return reply.model_dump_json()

    async def aclose(self) -> None:
        pass
