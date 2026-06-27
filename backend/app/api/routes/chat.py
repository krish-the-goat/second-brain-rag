from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from app.rag.pipeline import pipeline
from app.core.rate_limit import limiter

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    chat_history: List[ChatMessage] = Field(default=[], max_length=20)

@router.post("")
@limiter.limit("5/minute")
async def chat(body: ChatRequest, request: Request):
    history = [msg.model_dump() for msg in body.chat_history]
    result = await pipeline.ask(body.question, history)
    return result

@router.post("/stream")
@limiter.limit("5/minute")
async def chat_stream(body: ChatRequest, request: Request):
    history = [msg.model_dump() for msg in body.chat_history]
    return StreamingResponse(
        pipeline.ask_stream(body.question, history), 
        media_type="text/event-stream"
    )
