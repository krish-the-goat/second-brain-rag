from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any

from app.rag.pipeline import pipeline

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    chat_history: List[ChatMessage] = []

@router.post("")
async def chat(request: ChatRequest, req: Request):
    history = [msg.model_dump() for msg in request.chat_history]
    result = await pipeline.ask(request.question, history)
    return result

@router.post("/stream")
async def chat_stream(request: ChatRequest, req: Request):
    history = [msg.model_dump() for msg in request.chat_history]
    return StreamingResponse(
        pipeline.ask_stream(request.question, history), 
        media_type="text/event-stream"
    )
