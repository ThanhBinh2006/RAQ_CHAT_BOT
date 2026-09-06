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
from app.db.models import ChatMessage, ChatSession, Quiz, QuizQuestion

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

    import re

    def format_friendly_error(error_str: str, questions: list) -> str:
        err_lower = error_str.lower()
        if "resource_exhausted" in err_lower or "429" in err_lower or "quota" in err_lower:
            wait_seconds = None
            m = re.search(r"retry (?:in|after) ([\d\.]+)s", error_str, re.IGNORECASE)
            if m:
                try:
                    wait_seconds = round(float(m.group(1)))
                except Exception:
                    pass
            if not wait_seconds:
                m2 = re.search(r"['\"]retrydelay['\"]\s*:\s*['\"](\d+)s?['\"]", error_str, re.IGNORECASE)
                if m2:
                    try:
                        wait_seconds = int(m2.group(1))
                    except Exception:
                        pass

            time_str = f"**{wait_seconds} giây**" if wait_seconds else "khoảng **30 - 60 giây**"
            if questions:
                return (
                    f"Xin lỗi bạn, quá trình biên soạn câu hỏi bị gián đoạn do mô hình AI tạm thời đạt giới hạn số lượng yêu cầu (429 Resource Exhausted). Bạn vui lòng đợi {time_str} nữa nhé.\n\n"
                    f"💡 Hệ thống đã tự động lưu lại thành công **{len(questions)}** câu hỏi trắc nghiệm đã hoàn thành trước đó vào Thư viện để bạn có thể xem lại hoặc xuất đề thi."
                )
            else:
                return (
                    f"Xin lỗi bạn, hiện tại hệ thống AI đang gặp vấn đề về giới hạn số lượng yêu cầu tự động (vượt quá hạn mức sử dụng tạm thời - 429 Resource Exhausted).\n\n"
                    f"Hệ thống báo cần đợi khoảng {time_str} nữa. Bạn vui lòng thử lại sau một lát nhé!\n\n"
                    f"💡 *Mẹo: Bạn có thể nhập API Key cá nhân trong phần Cài đặt mô hình để có hạn mức riêng ổn định hơn.*"
                )

        if "api_key" in err_lower or "unauthenticated" in err_lower or "401" in err_lower or "403" in err_lower:
            return "Hệ thống không thể xác thực API Key của mô hình AI. Bạn vui lòng kiểm tra lại API Key trong menu Cài đặt và thử lại nhé."

        clean_err = error_str.split("\n")[0][:180]
        if questions:
            return (
                f"Đã xảy ra sự cố trong quá trình xử lý: {clean_err}.\n\n"
                f"💡 Hệ thống đã lưu lại thành công **{len(questions)}** câu hỏi trắc nghiệm đã hoàn thành trước đó để bạn có thể xem lại."
            )
        return f"Đã xảy ra sự cố trong quá trình xử lý yêu cầu: {clean_err}. Bạn vui lòng thử lại sau giây lát nhé."

    def extract_text_content(content: Any) -> str:
        if not content:
            return ""
        if isinstance(content, str):
            if ("'text':" in content or '"text":' in content) and (content.startswith("content=[") or content.startswith("[{")):
                match = re.search(r"['\"]text['\"]\s*:\s*['\"]([\s\S]*?)['\"]\s*[,}]", content)
                if match:
                    try:
                        return match.group(1).encode("utf-8").decode("unicode_escape", errors="ignore")
                    except Exception:
                        return match.group(1)
            return content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(str(part.get("text", "")))
                    elif "text" in part:
                        text_parts.append(str(part["text"]))
                    elif "content" in part:
                        text_parts.append(extract_text_content(part["content"]))
                elif hasattr(part, "text"):
                    text_parts.append(str(getattr(part, "text", "")))
                elif hasattr(part, "content"):
                    text_parts.append(extract_text_content(getattr(part, "content", "")))
            return "".join(text_parts)
        if isinstance(content, dict):
            if content.get("type") == "text":
                return str(content.get("text", ""))
            if "text" in content:
                return str(content["text"])
            if "content" in content:
                return extract_text_content(content["content"])
        if hasattr(content, "content"):
            return extract_text_content(getattr(content, "content", ""))
        if hasattr(content, "text"):
            return str(getattr(content, "text", ""))
        return str(content)

    async def save_quiz_to_db(quiz_questions: List[dict], lib_id: Optional[UUID], u_id: Optional[str]) -> Optional[UUID]:
        if not quiz_questions:
            return None
        try:
            async with AsyncSessionLocal() as db:
                new_quiz = Quiz(
                    id=uuid4(),
                    library_id=lib_id,
                    user_id=u_id,
                    title=f"Đề ôn tập {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                    total_questions=len(quiz_questions),
                    is_edited_by_user=False,
                )
                db.add(new_quiz)
                await db.flush()

                for idx, q in enumerate(quiz_questions):
                    db.add(QuizQuestion(
                        id=uuid4(),
                        quiz_id=new_quiz.id,
                        order_index=idx,
                        question_text=q.get("question_text", ""),
                        option_a=q.get("option_a", ""),
                        option_b=q.get("option_b", ""),
                        option_c=q.get("option_c", ""),
                        option_d=q.get("option_d", ""),
                        correct_answer=q.get("correct_answer", "A"),
                        explanation=q.get("explanation"),
                        source_page=q.get("source_page"),
                    ))
                await db.commit()
                return new_quiz.id
        except Exception as e:
            print(f"Error auto-saving quiz to DB: {e}")
            return None

    async def persist_chat_message_to_db(sess_uuid: UUID, content: str, cits: Optional[List[dict]], q_id: Optional[UUID]):
        try:
            async with AsyncSessionLocal() as db:
                asst_msg = ChatMessage(
                    id=uuid4(),
                    session_id=sess_uuid,
                    role="assistant",
                    content=content,
                    citations=cits,
                    quiz_id=q_id,
                )
                db.add(asst_msg)
                sess = await db.get(ChatSession, sess_uuid)
                if sess:
                    sess.updated_at = datetime.now(timezone.utc)
                await db.commit()
                print(f"✅ Đã lưu tin nhắn Assistant vào DB (quiz_id: {q_id})")
        except Exception as e:
            print(f"Error persisting assistant message to DB: {e}")

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
            # ── XỬ LÝ LỖI (Rate limit 429, Resource Exhausted, v.v... thành tin nhắn thông thường) ──
            text_to_stream = format_friendly_error(error_detail, accumulated_quiz_questions)
            if accumulated_quiz_questions:
                quiz_draft = accumulated_quiz_questions
            citations = latest_citations
        else:
            # ── XỬ LÝ THÀNH CÔNG BÌNH THƯỜNG ──
            messages = final_state.get("messages", []) if isinstance(final_state, dict) else []
            for msg in reversed(messages):
                c_val = getattr(msg, "content", None)
                if c_val is None and isinstance(msg, dict):
                    c_val = msg.get("content")

                c_str = extract_text_content(c_val)

                m_type = getattr(msg, "type", None)
                if m_type is None and isinstance(msg, dict):
                    m_type = msg.get("type") or msg.get("role")

                if c_str.strip() and m_type not in ("tool", "system", "human", "user"):
                    text_to_stream = c_str
                    break

            if not text_to_stream and messages:
                for msg in reversed(messages):
                    c_val = getattr(msg, "content", None)
                    if c_val is None and isinstance(msg, dict):
                        c_val = msg.get("content")
                    c_str = extract_text_content(c_val)
                    if c_str.strip():
                        text_to_stream = c_str
                        break

            # Lấy quiz_draft từ final_state hoặc từ các batch đã tích lũy
            final_quiz = final_state.get("quiz_draft") if isinstance(final_state, dict) else None
            if final_quiz and isinstance(final_quiz, list) and len(final_quiz) > 0:
                quiz_draft = final_quiz
            elif accumulated_quiz_questions:
                quiz_draft = accumulated_quiz_questions

            if not text_to_stream:
                if quiz_draft:
                    text_to_stream = f"Đã hoàn thành biên soạn {len(quiz_draft)} câu hỏi trắc nghiệm bám sát tài liệu."
                else:
                    text_to_stream = "Đã hoàn thành xử lý yêu cầu."

            citations = (final_state.get("citations") if isinstance(final_state, dict) else None) or latest_citations

        # 3. Tự động lưu Quiz vào DB (nếu có câu hỏi)
        saved_quiz_id = None
        if quiz_draft and session_uuid:
            lib_id = UUID(request.libraryId) if request.libraryId else None
            saved_quiz_id = await save_quiz_to_db(quiz_draft, lib_id, user_id)

        # 4. Gửi tín hiệu quiz_ready ngay lập tức về Frontend để FE xuống DB lấy lên (không cần reload)
        if saved_quiz_id:
            event_json = json.dumps({"type": "quiz_ready", "quiz_id": str(saved_quiz_id)}, ensure_ascii=False)
            yield f"<!--EVENT:{event_json}-->\n"

        # 5. Lưu tin nhắn Assistant vào DB SONG SONG với quá trình stream (Background Task)
        if session_uuid and text_to_stream:
            asyncio.create_task(persist_chat_message_to_db(session_uuid, text_to_stream, citations, saved_quiz_id))

        # 6. Stream text mượt mà về Frontend song song
        words = text_to_stream.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == len(words) - 1 else word + " "
            yield chunk
            await asyncio.sleep(0.015)

        # 7. Gửi metadata (quiz_id, citations) về Frontend
        meta: Dict[str, Any] = {}
        if saved_quiz_id:
            meta["quiz_id"] = str(saved_quiz_id)
        if citations:
            meta["citations"] = citations

        if meta:
            meta_json_str = json.dumps(meta, ensure_ascii=False)
            yield f"\n\n<!--METADATA_START-->{meta_json_str}<!--METADATA_END-->"

    return StreamingResponse(generate_stream(), media_type="text/plain")
