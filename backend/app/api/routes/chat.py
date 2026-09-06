from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

from app.agents.assistant.graph import build_assistant_graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.security import decode_access_token
from app.core.config import settings

router = APIRouter()

from uuid import UUID, uuid4
from datetime import datetime, timezone
from app.core.db import AsyncSessionLocal
from app.db.models import ChatMessage, ChatSession

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    libraryId: Optional[str] = None
    sessionId: Optional[str] = None

@router.post("/chat")
async def chat_endpoint(request: ChatRequest, req: Request):
    """
    Vercel AI SDK compatible streaming endpoint with DB persistence.
    """
    # Extract user_id from JWT Authorization header
    user_id = None
    auth_header = req.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        user_id = decode_access_token(token)

    session_uuid: Optional[UUID] = None
    if request.sessionId:
        try:
            session_uuid = UUID(request.sessionId)
        except Exception:
            session_uuid = None

    # Convert Vercel AI messages to LangChain messages
    lc_messages = []
    latest_user_text = ""
    for m in request.messages:
        role = m.get("role")
        content = m.get("content", "")
        if not content and "parts" in m:
            parts = m.get("parts") or []
            content = "".join([p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"])

        if role == "user":
            latest_user_text = content
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            # Bỏ tag metadata nếu có trong tin nhắn cũ để LLM không bị nhiễu
            clean_content = content
            idx = clean_content.find("<!--METADATA_START-->")
            if idx != -1:
                clean_content = clean_content[:idx].strip()
            lc_messages.append(AIMessage(content=clean_content))
        elif role == "system":
            lc_messages.append(SystemMessage(content=content))

    # Lưu tin nhắn của User vào DB
    if session_uuid and latest_user_text:
        try:
            async with AsyncSessionLocal() as db:
                user_msg = ChatMessage(
                    id=uuid4(),
                    session_id=session_uuid,
                    role="user",
                    content=latest_user_text,
                )
                db.add(user_msg)

                # Tự động cập nhật tiêu đề session theo câu hỏi đầu tiên
                chat_sess = await db.get(ChatSession, session_uuid)
                if chat_sess:
                    if not chat_sess.title or chat_sess.title == "Đoạn chat mới":
                        clean_title = latest_user_text.strip().replace("\n", " ")
                        chat_sess.title = (clean_title[:35] + "...") if len(clean_title) > 35 else clean_title
                    chat_sess.updated_at = datetime.now(timezone.utc)
                await db.commit()
        except Exception as e:
            print(f"Error saving user message to DB: {e}")

    # Parse headers for API keys (User is ONLY allowed to provide gemini, openai, anthropic keys)
    user_api_keys = {}
    for provider in ["gemini", "openai", "anthropic"]:
        val = req.headers.get(f"X-{provider.capitalize()}-Key")
        if val:
            user_api_keys[provider] = val

    final_api_keys = {
        "gemini": user_api_keys.get("gemini"),
        "openai": user_api_keys.get("openai"),
        "anthropic": user_api_keys.get("anthropic"),
        # Default and embedding keys are strictly system-only; user cannot touch or override them
        "default": settings.SYSTEM_DEFAULT_API_KEY,
        "default_embed": settings.SYSTEM_DEFAULT_EMBEDDING_KEY,
    }

    model_config = {}
    for role_name in ["supervisor", "generator", "evaluator", "synthesizer"]:
        val = req.headers.get(f"X-{role_name.capitalize()}-Model")
        if val:
            model_config[role_name] = val

    default_model_config = {
        "supervisor": settings.DEFAULT_CHAT_MODEL,
        "generator": settings.DEFAULT_CHAT_MODEL,
        "evaluator": settings.DEFAULT_CHAT_MODEL,
        "synthesizer": settings.DEFAULT_CHAT_MODEL,
    }
    final_model_config = {
        **default_model_config,
        **model_config,
        # Embedding model is strictly system-only; user cannot touch or override it
        "embed": settings.DEFAULT_EMBEDDING_MODEL,
    }

    # Initialize graph
    graph = build_assistant_graph()
    
    state = {
        "messages": lc_messages,
        "library_id": request.libraryId,
        "session_id": request.sessionId,
        "user_id": user_id,
        "api_keys": final_api_keys,
        "model_config": final_model_config,
    }

    def extract_text_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif "text" in part:
                        text_parts.append(str(part["text"]))
                elif hasattr(part, "text"):
                    text_parts.append(str(getattr(part, "text", "")))
            return "".join(text_parts)
        return str(content) if content else ""

    async def generate_stream():
        import asyncio
        event_queue = asyncio.Queue()
        state["event_queue"] = event_queue
        accumulated_quiz_questions: List[dict] = []
        latest_citations: Optional[List[dict]] = None
        error_occurred = False
        error_detail = ""

        async def run_agent():
            try:
                res = await graph.ainvoke(state)
                await event_queue.put({"type": "__GRAPH_DONE__", "result": res})
            except Exception as err:
                print(f"Error executing agent graph: {err}")
                await event_queue.put({"type": "__GRAPH_ERROR__", "error": str(err)})

        agent_task = asyncio.create_task(run_agent())

        final_state = None
        while True:
            try:
                event = await event_queue.get()
            except Exception as e:
                error_occurred = True
                error_detail = str(e)
                break

            if not event:
                continue
            event_type = event.get("type")
            if event_type == "__GRAPH_DONE__":
                final_state = event.get("result")
                break
            elif event_type == "__GRAPH_ERROR__":
                error_occurred = True
                error_detail = event.get("error", "Đã xảy ra lỗi khi xử lý yêu cầu.")
                break
            elif event_type == "quiz_batch":
                questions = event.get("questions") or []
                if isinstance(questions, list):
                    accumulated_quiz_questions.extend(questions)
                event_json = json.dumps(event, ensure_ascii=False)
                yield f"<!--EVENT:{event_json}-->\n"
            elif event_type == "tool_status":
                if event.get("citations"):
                    latest_citations = event.get("citations")
                event_json = json.dumps(event, ensure_ascii=False)
                yield f"<!--EVENT:{event_json}-->\n"

        # Đợi agent task kết thúc nếu vẫn đang chạy ngầm
        if not agent_task.done():
            try:
                await asyncio.wait_for(agent_task, timeout=1.5)
            except Exception:
                pass

        # 2. Xử lý nội dung văn bản phản hồi và bộ đề trắc nghiệm
        text_to_stream = ""
        quiz_draft = None
        citations = None

        if error_occurred or not final_state:
            # ── XỬ LÝ LỖI (Bất kỳ trường hợp nào, không chỉ quiz) ──
            if accumulated_quiz_questions:
                text_to_stream = (
                    f"Đã xảy ra sự cố trong quá trình xử lý: {error_detail or 'Không thể hoàn thành toàn bộ đợt sinh câu hỏi'}.\n\n"
                    f"💡 Hệ thống đã lưu lại thành công {len(accumulated_quiz_questions)} câu hỏi trắc nghiệm đã hoàn thành trước khi gặp lỗi để bạn có thể xem lại hoặc xuất đề."
                )
                quiz_draft = accumulated_quiz_questions
            else:
                text_to_stream = f"Đã xảy ra lỗi trong quá trình xử lý yêu cầu: {error_detail or 'Hệ thống không nhận được phản hồi hợp lệ từ mô hình.'}"
            citations = latest_citations
        else:
            # ── XỬ LÝ THÀNH CÔNG BÌNH THƯỜNG ──
            messages = final_state.get("messages", [])
            for msg in reversed(messages):
                # Ưu tiên lấy tin nhắn từ AI (AIMessage) có chứa nội dung
                content_str = extract_text_content(getattr(msg, "content", ""))
                if content_str.strip() and getattr(msg, "type", "") != "tool":
                    text_to_stream = content_str
                    break

            if not text_to_stream and messages:
                text_to_stream = extract_text_content(getattr(messages[-1], "content", ""))

            # Lấy quiz_draft từ final_state hoặc từ các batch đã tích lũy
            final_quiz = final_state.get("quiz_draft")
            if final_quiz and isinstance(final_quiz, list) and len(final_quiz) > 0:
                quiz_draft = final_quiz
            elif accumulated_quiz_questions:
                quiz_draft = accumulated_quiz_questions

            if not text_to_stream:
                if quiz_draft:
                    text_to_stream = f"Đã hoàn thành biên soạn {len(quiz_draft)} câu hỏi trắc nghiệm bám sát tài liệu."
                else:
                    text_to_stream = "Đã hoàn thành xử lý yêu cầu."

            citations = final_state.get("citations") or latest_citations

        # 3. Stream text mượt mà về Frontend
        words = text_to_stream.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == len(words) - 1 else word + " "
            yield chunk
            await asyncio.sleep(0.015)

        # 4. Gửi kèm quiz_draft và citations nếu có để Frontend render card tương ứng
        meta_json_str = ""
        if quiz_draft or citations:
            meta: Dict[str, Any] = {}
            if quiz_draft:
                meta["quiz_draft"] = quiz_draft
            if citations:
                meta["citations"] = citations

            def serialize_meta(val: Any) -> Any:
                if hasattr(val, "model_dump"):
                    return val.model_dump()
                if hasattr(val, "dict"):
                    return val.dict()
                if isinstance(val, list):
                    return [serialize_meta(item) for item in val]
                if isinstance(val, dict):
                    return {k: serialize_meta(v) for k, v in val.items()}
                return val

            meta_json_str = json.dumps(serialize_meta(meta), ensure_ascii=False)
            yield f"\n\n<!--METADATA_START-->{meta_json_str}<!--METADATA_END-->"

        # 5. LUÔN LUÔN lưu tin nhắn của Assistant vào DB (kể cả khi gặp lỗi) để khi reload không bao giờ bị mất
        if session_uuid and text_to_stream:
            try:
                full_saved_content = text_to_stream
                if meta_json_str:
                    full_saved_content += f"\n\n<!--METADATA_START-->{meta_json_str}<!--METADATA_END-->"

                async with AsyncSessionLocal() as db:
                    asst_msg = ChatMessage(
                        id=uuid4(),
                        session_id=session_uuid,
                        role="assistant",
                        content=full_saved_content,
                        citations=citations,
                    )
                    db.add(asst_msg)
                    sess = await db.get(ChatSession, session_uuid)
                    if sess:
                        sess.updated_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception as e:
                print(f"Error saving assistant message to DB: {e}")

    return StreamingResponse(generate_stream(), media_type="text/plain")
