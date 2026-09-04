"""
Tool 1: search_documents — RAG search using Command pattern.
"""

from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState


@tool
async def search_documents(
    query: str,
    state: Annotated[dict, InjectedState],
) -> dict:
    """Tìm đoạn văn bản liên quan trong tài liệu của Thư viện hiện tại để trả lời
    câu hỏi kiến thức của người dùng. LUÔN dùng tool này khi người dùng hỏi về
    nội dung tài liệu, nhờ giải thích, tóm tắt, hoặc tra cứu thông tin cụ thể."""

    from app.services.vector_store import similarity_search

    # Lấy key riêng cho Embedding và LLM nếu người dùng cung cấp (BYOK)
    api_keys = state.get("api_keys", {})
    embedding_key = api_keys.get("nvidia_embedding") or api_keys.get("nvidia") or api_keys.get("gemini")
    llm_key = api_keys.get("nvidia") or api_keys.get("gemini")

    library_id = state.get("library_id")
    user_id = state.get("user_id")

    chunks = await similarity_search(
        query=query,
        library_id=library_id,
        user_id=user_id,
        top_k=10,
        api_key=embedding_key,
        llm_api_key=llm_key,
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

    return {
        "citations": citations,
        "context_text": context_text,
    }
