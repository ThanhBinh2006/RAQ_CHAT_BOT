from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

from app.agents.assistant.graph import build_assistant_graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.security import decode_access_token

router = APIRouter()

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    libraryId: Optional[str] = None
    sessionId: Optional[str] = None

@router.post("/chat")
async def chat_endpoint(request: ChatRequest, req: Request):
    """
    Vercel AI SDK compatible streaming endpoint.
    """
    # Extract user_id from JWT Authorization header
    user_id = None
    auth_header = req.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        user_id = decode_access_token(token)

    # Convert Vercel AI messages to LangChain messages
    lc_messages = []
    for m in request.messages:
        role = m.get("role")
        content = m.get("content", "")
        if not content and "parts" in m:
            parts = m.get("parts") or []
            content = "".join([p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"])

        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        elif role == "system":
            lc_messages.append(SystemMessage(content=content))

    # Parse headers for API keys and Model configs
    api_keys = {}
    for provider in ["gemini", "groq", "openai", "anthropic"]:
        val = req.headers.get(f"X-{provider.capitalize()}-Key")
        if val:
            api_keys[provider] = val

    model_config = {}
    for role_name in ["supervisor", "generator", "evaluator", "synthesizer"]:
        val = req.headers.get(f"X-{role_name.capitalize()}-Model")
        if val:
            model_config[role_name] = val

    default_model_config = {
        "supervisor": "gemini-2.5-flash",
        "generator": "gemini-2.5-flash",
        "evaluator": "gemini-2.5-flash",
        "synthesizer": "gemini-2.5-flash",
    }
    final_model_config = {**default_model_config, **model_config}

    # Initialize graph
    graph = build_assistant_graph()
    
    state = {
        "messages": lc_messages,
        "library_id": request.libraryId,
        "session_id": request.sessionId,
        "user_id": user_id,
        "api_keys": api_keys if api_keys else {},
        "model_config": final_model_config,
    }

    async def generate_stream():
        import asyncio
        # 1. Chạy hoàn tất toàn bộ LangGraph ReAct agent & tools trước để có kết quả đầy đủ
        final_state = await graph.ainvoke(state)

        # 2. Lấy nội dung câu trả lời cuối cùng của Assistant và stream về Frontend
        messages = final_state.get("messages", [])
        if messages:
            last_message = messages[-1]
            content = last_message.content
            if content and isinstance(content, str):
                # Tách thành từng từ để stream mượt mà về client
                words = content.split(" ")
                for i, word in enumerate(words):
                    chunk = word if i == len(words) - 1 else word + " "
                    yield chunk
                    await asyncio.sleep(0.015)

    return StreamingResponse(generate_stream(), media_type="text/plain")
