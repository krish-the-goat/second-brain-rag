from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List

from app.rag.pipeline import pipeline
from app.core.rate_limit import limiter, CHAT_RATE_LIMIT
from app.core.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatMessage(BaseModel):
    role: str = Field(..., max_length=20)
    content: str = Field(..., max_length=4000)

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    chat_history: List[ChatMessage] = Field(default=[], max_length=20)

@router.post("")
@limiter.limit(CHAT_RATE_LIMIT)
async def chat(
    body: ChatRequest,
    request: Request,
    user_id: int = Depends(get_current_user),
):
    history = [msg.model_dump() for msg in body.chat_history]
    result = await pipeline.ask(body.question, history, owner_id=str(user_id))
    return result

@router.post("/stream")
@limiter.limit(CHAT_RATE_LIMIT)
async def chat_stream(
    body: ChatRequest,
    request: Request,
    user_id: int = Depends(get_current_user),
):
    history = [msg.model_dump() for msg in body.chat_history]
    return StreamingResponse(
        pipeline.ask_stream(body.question, history, owner_id=str(user_id)), 
        media_type="text/event-stream"
    )
