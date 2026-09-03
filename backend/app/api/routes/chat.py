from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

from app.agents.assistant.graph import build_assistant_graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

router = APIRouter()

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    libraryId: Optional[str] = None
    sessionId: Optional[str] = None

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Vercel AI SDK compatible streaming endpoint.
    """
    # Convert Vercel AI messages to LangChain messages
    lc_messages = []
    for m in request.messages:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))
        elif m["role"] == "system":
            lc_messages.append(SystemMessage(content=m["content"]))

    # Initialize graph
    graph = build_assistant_graph()
    
    state = {
        "messages": lc_messages,
        "library_id": request.libraryId,
        "session_id": request.sessionId,
        # TODO: Add logic to fetch api_keys from DB/Session if needed
    }

    async def generate_stream():
        # Vercel AI SDK Data Stream Protocol: 
        # 0: Text chunk
        # 8: Custom JSON object data
        
        async for event in graph.astream_events(state, version="v2"):
            kind = event["event"]
            
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content and isinstance(chunk.content, str):
                    # Format as Vercel AI SDK text chunk
                    yield f'0:{json.dumps(chunk.content)}\n'
                    
            elif kind == "on_chain_end":
                if event["name"] == "tools":
                    # If tools updated state (e.g. quiz_draft), send it as data
                    tool_output_state = event["data"]["output"]
                    if tool_output_state and "quiz_draft" in tool_output_state:
                        custom_data = [{"quiz_draft": tool_output_state["quiz_draft"]}]
                        yield f'8:{json.dumps(custom_data)}\n'

    return StreamingResponse(generate_stream(), media_type="text/event-stream")
