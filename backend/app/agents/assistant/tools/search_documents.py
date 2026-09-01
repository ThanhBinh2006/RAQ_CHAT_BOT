"""
Tool 1: search_documents — RAG search using Command pattern.
"""

from typing import Annotated
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langchain_core.tools import InjectedToolCallId
from langgraph.types import Command


@tool
async def search_documents(
    query: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Tìm đoạn văn bản liên quan trong tài liệu của Thư viện hiện tại để trả lời
    câu hỏi kiến thức của người dùng. LUÔN dùng tool này khi người dùng hỏi về
    nội dung tài liệu, nhờ giải thích, tóm tắt, hoặc tra cứu thông tin cụ thể."""

    from app.services.vector_store import similarity_search

    # Get optional user Gemini key for embedding
    api_keys = state.get("api_keys", {})
    gemini_key = api_keys.get("gemini")

    chunks = await similarity_search(
        query=query,
        library_id=state["library_id"],
        user_id=state["user_id"],
        top_k=6,
        api_key=gemini_key,
    )

    citations = [
        {"page_number": c["page_number"], "document_id": c["document_id"]}
        for c in chunks
    ]
    context_text = "\n\n".join(
        f"[Trang {c['page_number']}] {c['content']}" for c in chunks
    )

    if not context_text:
        context_text = "Không tìm thấy tài liệu liên quan. Vui lòng thử lại với từ khóa khác."

    return Command(update={
        "citations": citations,
        "messages": [ToolMessage(content=context_text, tool_call_id=tool_call_id)],
    })
