from fastapi import APIRouter, Request

from app.domain.models import Capabilities, ChatRequest, ChatResponse, Health

router = APIRouter(prefix="/api/v0")


@router.get("/health", response_model=Health)
async def health(request: Request) -> Health:
    settings = request.app.state.settings
    return Health(
        provider=settings.llm_provider, capabilities=Capabilities(chat=settings.chat_available)
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    return await request.app.state.conversation.chat(body)
