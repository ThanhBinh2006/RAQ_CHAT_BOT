# 🏗️ Kiến trúc Chi tiết Chatbot Supervisor v2 (Hợp nhất)

> **Nguyên tắc hợp nhất:** Giữ nguyên khung sườn của kiến trúc gốc (naming `library`, 9 bảng theo mô hình Thư viện độc lập, 1 graph LangGraph duy nhất đăng ký với CopilotKit) làm **chuẩn**. Bổ sung 3 phần "hay" từ bản thiết kế thứ hai: **(1)** DDL SQL đầy đủ có index vector, **(2)** cách hiện thực node bằng pattern `Command` + `InjectedState`/`InjectedToolCallId` (idiom mới của LangGraph, gọn hơn dict thường), **(3)** luồng sửa đáp án + lưu Quiz hoàn chỉnh (được yêu cầu ở lượt trước nhưng chưa có code).

---

## 1. Cấu trúc thư mục (bản đầy đủ, giữ naming `library`)

```
backend/
├── app/
│   ├── main.py                       # FastAPI + đăng ký 1 LangGraphAgent duy nhất
│   ├── core/
│   │   ├── config.py                 # .env Settings
│   │   ├── security.py               # JWT
│   │   └── db.py                     # Async SQLAlchemy engine
│   ├── db/
│   │   └── models.py                 # 9 ORM models (users, libraries, documents...)
│   ├── schemas/
│   │   ├── auth.py / library.py / document.py / chat.py
│   │   └── quiz.py                   # Pydantic Strict Schema + request/response API
│   ├── api/
│   │   ├── deps.py                   # get_current_user, get_db
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── libraries.py          # CRUD library + chat_sessions
│   │       ├── documents.py          # Upload PDF, progress
│   │       ├── quizzes.py            # ⭐ POST/GET /quizzes (lưu bản đã sửa)
│   │       └── copilotkit.py         # Mount endpoint CopilotKit
│   ├── services/
│   │   ├── storage_service.py        # MinIO
│   │   ├── ingestion_service.py      # PyMuPDF + splitter + embed
│   │   └── vector_store.py           # similarity_search theo library_id + user_id
│   ├── llm/
│   │   └── llm_factory.py            # Dynamic BYOK 2-tier, per-role model
│   └── agents/
│       └── assistant/                # ⭐ 1 GRAPH DUY NHẤT đăng ký CopilotKit
│           ├── state.py              # AgentState
│           ├── graph.py              # agent_node (bind_tools) ⇄ ToolNode
│           ├── prompts.py            # system prompt + few-shot chọn tool
│           └── tools/
│               ├── search_documents.py     # Tool 1 (RAG) - Command pattern
│               └── generate_quiz/
│                   ├── tool.py              # Tool 2 - gọi quiz_subgraph.invoke()
│                   ├── state.py             # QuizState (nội bộ)
│                   ├── schemas.py           # DraftQuestionBatch, EvaluationResult...
│                   ├── subgraph.py          # StateGraph batching + reflection
│                   └── nodes/
│                       ├── generator_node.py
│                       ├── evaluator_node.py
│                       └── synthesizer_node.py
├── alembic/versions/…
├── tests/
└── requirements.txt

frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx                 # <CopilotKit runtimeUrl agent="assistant">
│   │   └── libraries/[id]/page.tsx    # Bố cục 3 cột NotebookLM-style
│   ├── components/
│   │   ├── library/LibrarySidebar.tsx     # Cột 1: danh sách file + progress bar
│   │   ├── library/SessionList.tsx        # Cột 2: các đoạn chat
│   │   ├── chat/ChatWindow.tsx            # Cột 3: 1 khung chat duy nhất
│   │   ├── quiz/QuizPreviewCard.tsx        # Generative UI khi quiz_draft xuất hiện
│   │   ├── quiz/QuizEditorCard.tsx         # ⭐ Sửa từng câu + Lưu / Xuất PDF
│   │   ├── quiz/QuizPdfExport.tsx          # jsPDF / react-pdf client-side
│   │   └── settings/ApiKeySettingsModal.tsx
│   ├── lib/api.ts                     # axios instance + interceptor gắn headers
│   └── hooks/useAssistant.ts          # useCoAgent<AgentState>("assistant")
└── package.json
```

---

## 2. Database DDL đầy đủ (PostgreSQL + pgvector, naming `library`)

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE libraries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon_or_color VARCHAR(50),
    total_documents INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_libraries_user ON libraries(user_id);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    library_id UUID NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name VARCHAR(500) NOT NULL,
    file_path_minio TEXT NOT NULL,
    total_pages INT,
    status VARCHAR(30) DEFAULT 'pending',   -- pending | processing | ready | failed
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_documents_library ON documents(library_id);

CREATE TABLE ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    total_chunks INT DEFAULT 0,
    processed_chunks INT DEFAULT 0,
    progress_percent NUMERIC(5,2) DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    library_id UUID NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    page_number INT,
    chunk_index INT,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    metadata JSONB
);
CREATE INDEX idx_chunks_library_user ON document_chunks(library_id, user_id);
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    library_id UUID NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL CHECK (role IN ('user','assistant')),
    content TEXT NOT NULL,
    citations JSONB,
    quiz_id UUID REFERENCES quizzes(id),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_messages_session ON chat_messages(session_id, created_at);

CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    library_id UUID NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    description TEXT,
    total_questions INT,
    is_edited_by_user BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE quiz_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    order_index INT NOT NULL,
    question_text TEXT NOT NULL,
    option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
    correct_answer CHAR(1) CHECK (correct_answer IN ('A','B','C','D')),
    explanation TEXT,
    source_page INT
);
CREATE INDEX idx_questions_quiz ON quiz_questions(quiz_id, order_index);
```

> Lưu ý thứ tự: vì `chat_messages.quiz_id` tham chiếu `quizzes`, hãy tạo bảng `quizzes` trước `chat_messages` khi chạy script thật (thứ tự ở trên chỉ để đọc theo mạch nghiệp vụ).
>
> `AsyncPostgresSaver` của LangGraph sẽ tự `CREATE TABLE checkpoints, checkpoint_writes, checkpoint_blobs` khi gọi `.setup()` — không cần viết DDL tay cho phần này.

---

## 3. LangGraph — 1 Agent duy nhất, dùng pattern Tool-Calling chuẩn (`ToolNode` + `Command`)

### 3.1 State (`agents/assistant/state.py`)

```python
from typing import TypedDict, Annotated, Optional, List
from langgraph.graph.message import add_messages

class ModelConfig(TypedDict):
    supervisor: str
    generator: str
    evaluator: str
    synthesizer: str

class ApiKeys(TypedDict, total=False):
    gemini: str
    groq: str
    openai: str
    anthropic: str

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    library_id: str
    session_id: str
    model_config: ModelConfig
    api_keys: ApiKeys
    citations: Optional[List[dict]]
    quiz_draft: Optional[List[dict]]     # kết quả tool generate_quiz, đẩy sang CopilotKit render
```

### 3.2 Tool 1 — `search_documents` (RAG, dùng `Command` để cập nhật state trực tiếp)

```python
# agents/assistant/tools/search_documents.py
from typing import Annotated
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.prebuilt.tool_node import InjectedToolCallId
from langgraph.types import Command
from app.services.vector_store import similarity_search

@tool
def search_documents(
    query: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Tìm đoạn văn bản liên quan trong tài liệu của Thư viện hiện tại để trả lời
    câu hỏi kiến thức của người dùng. LUÔN dùng tool này khi người dùng hỏi về
    nội dung tài liệu, nhờ giải thích, tóm tắt, hoặc tra cứu thông tin cụ thể."""
    chunks = similarity_search(
        query=query,
        library_id=state["library_id"],
        user_id=state["user_id"],
        top_k=6,
    )
    citations = [{"page_number": c["page_number"], "document_id": c["document_id"]} for c in chunks]
    context_text = "\n\n".join(f"[Trang {c['page_number']}] {c['content']}" for c in chunks)

    return Command(update={
        "citations": citations,
        "messages": [ToolMessage(content=context_text, tool_call_id=tool_call_id)],
    })
```

### 3.3 Tool 2 — `generate_quiz` (gọi `quiz_subgraph` bên trong, ẩn cụm 3-agent)

```python
# agents/assistant/tools/generate_quiz/tool.py
from typing import Annotated, Optional
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.prebuilt.tool_node import InjectedToolCallId
from langgraph.types import Command
from .subgraph import quiz_subgraph

@tool
def generate_quiz(
    num_questions: int,
    focus_topic: Optional[str],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Sinh bộ đề trắc nghiệm N câu (tối đa 100) bám sát tài liệu trong Thư viện
    hiện tại. Dùng tool này khi người dùng yêu cầu 'tạo đề', 'tạo N câu trắc nghiệm',
    'sinh câu hỏi ôn tập', kèm chủ đề trọng tâm nếu có."""
    n = min(num_questions, 100)
    result = quiz_subgraph.invoke({
        "library_id": state["library_id"],
        "user_id": state["user_id"],
        "focus_topic": focus_topic,
        "num_questions": n,
        "batch_size": 18,
        "current_batch": 0,
        "retry_count": 0,
        "context_chunks": [],
        "accepted_questions": [],
        "model_config": state["model_config"],
        "api_keys": state["api_keys"],
    })
    return Command(update={
        "quiz_draft": result["accepted_questions"],
        "messages": [ToolMessage(
            content=f"Đã sinh xong {len(result['accepted_questions'])} câu hỏi trắc nghiệm.",
            tool_call_id=tool_call_id,
        )],
    })
```

### 3.4 Quiz Subgraph — batching + reflection (giữ nguyên thiết kế gốc)

```python
# agents/assistant/tools/generate_quiz/subgraph.py
from langgraph.graph import StateGraph, START, END
from .state import QuizState
from .nodes.generator_node import generator_node
from .nodes.evaluator_node import evaluator_node
from .nodes.synthesizer_node import synthesizer_node

MAX_RETRY_PER_BATCH = 2

def init_batch_plan(state: QuizState):
    total = -(-state["num_questions"] // state["batch_size"])  # ceil
    return {"total_batches": total}

def should_continue_after_eval(state: QuizState):
    if state["eval_feedback"] == "approved":
        return "synthesizer"
    if state["retry_count"] >= MAX_RETRY_PER_BATCH:
        return "synthesizer"   # chấp nhận bản tốt nhất, tránh loop vô hạn
    return "generator"          # reflection: sinh lại kèm feedback cụ thể

def has_more_batches(state: QuizState):
    return "generator" if len(state["accepted_questions"]) < state["num_questions"] else END

graph = StateGraph(QuizState)
graph.add_node("init", init_batch_plan)
graph.add_node("generator", generator_node)
graph.add_node("evaluator", evaluator_node)
graph.add_node("synthesizer", synthesizer_node)
graph.add_edge(START, "init")
graph.add_edge("init", "generator")
graph.add_edge("generator", "evaluator")
graph.add_conditional_edges("evaluator", should_continue_after_eval,
                             {"generator": "generator", "synthesizer": "synthesizer"})
graph.add_conditional_edges("synthesizer", has_more_batches,
                             {"generator": "generator", END: END})
quiz_subgraph = graph.compile()
```

`generator_node` / `evaluator_node` / `synthesizer_node` giữ nguyên logic đã có ở bản v1 (Generator dùng model Groq tốc độ nhanh cho draft, Evaluator + Synthesizer dùng Gemini 2.5 Flash cho độ chính xác + Structured Output) — chỉ khác state field name khớp `QuizState` ở trên. Nếu bạn muốn, mình viết lại đủ 3 file này trong lượt sau.

### 3.5 Graph chính — Agent ⇄ Tools (ReAct loop chuẩn LangGraph)

```python
# agents/assistant/graph.py
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
from app.llm.llm_factory import get_llm
from .state import AgentState
from .prompts import SYSTEM_PROMPT
from .tools.search_documents import search_documents
from .tools.generate_quiz.tool import generate_quiz

TOOLS = [search_documents, generate_quiz]

def agent_node(state: AgentState):
    llm = get_llm(state["model_config"]["supervisor"], state["api_keys"])
    llm_with_tools = llm.bind_tools(TOOLS)
    messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def build_assistant_graph(checkpointer=None):
    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(TOOLS))
    g.set_entry_point("agent")
    g.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    g.add_edge("tools", "agent")   # sau khi tool chạy, quay lại agent để tổng hợp câu trả lời
    return g.compile(checkpointer=checkpointer)
```

```python
# agents/assistant/prompts.py
SYSTEM_PROMPT = """Bạn là trợ lý học tập của một Thư viện tài liệu.
- Nếu người dùng hỏi kiến thức / nhờ giải thích / tóm tắt nội dung tài liệu → gọi tool `search_documents`.
- Nếu người dùng yêu cầu tạo đề thi / câu hỏi trắc nghiệm / bài ôn tập → gọi tool `generate_quiz`
  với `num_questions` và `focus_topic` trích xuất từ yêu cầu (mặc định 10 câu nếu không nói rõ số lượng).
- Nếu người dùng chỉ chào hỏi / hỏi ngoài lề → trả lời trực tiếp, KHÔNG gọi tool.
Luôn trả lời bằng tiếng Việt, ngắn gọn, có trích dẫn số trang khi dùng search_documents.
"""
```

**Vì sao pattern này "hay" hơn router thủ công:** `tools_condition` (prebuilt) tự kiểm tra `AIMessage` cuối có `tool_calls` hay không để rẽ nhánh — không cần tự viết node phân loại ý định bằng structured-output riêng. LLM vừa đóng vai supervisor vừa tự quyết định gọi tool nào, đúng với đặc tả README ("Tool 1", "Tool 2"), đồng thời vẫn cho phép trả lời trực tiếp (chitchat) khi không cần tool nào — gộp cả 3 nhánh cũ (`rag`/`quiz`/`chitchat`) vào một vòng lặp duy nhất.

---

## 4. Postgres Checkpointer (giữ nguyên từ v1)

```python
# core/db.py
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def get_checkpointer():
    async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as saver:
        await saver.setup()
        return saver
```

`thread_id = session_id` → mỗi đoạn chat resume đúng vị trí nếu người dùng đóng tab giữa lúc đang sinh 100 câu (nhiều batch).

---

## 5. Đăng ký CopilotKit (1 agent duy nhất)

```python
# api/routes/copilotkit.py
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from app.agents.assistant.graph import build_assistant_graph

def register_copilotkit(app, checkpointer):
    sdk = CopilotKitRemoteEndpoint(agents=[
        LangGraphAgent(
            name="assistant",
            description="Trợ lý Thư viện: trả lời câu hỏi dựa trên tài liệu và tự tạo đề trắc nghiệm khi được yêu cầu",
            graph=build_assistant_graph(checkpointer),
        )
    ])
    add_fastapi_endpoint(app, sdk, "/api/copilotkit")
```

Header `X-Generator-Model`, `X-Evaluator-Model`, `X-Synthesizer-Model`, `X-Gemini-Key`, `X-Groq-Key`... được đọc ở middleware và inject vào `config["configurable"]` → nạp vào `state["model_config"]` / `state["api_keys"]` khi graph khởi chạy.

---

## 6. ⭐ Luồng Sửa Đáp Án & Lưu Quiz (phần còn thiếu, bổ sung đầy đủ)

### 6.1 Backend — Schema request/response (`schemas/quiz.py`)

```python
from pydantic import BaseModel
from typing import Literal, Optional
from uuid import UUID

class QuizQuestionIn(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: Literal["A", "B", "C", "D"]
    explanation: Optional[str] = None
    source_page: Optional[int] = None

class QuizCreateRequest(BaseModel):
    library_id: UUID
    title: str
    description: Optional[str] = None
    questions: list[QuizQuestionIn]
    is_edited_by_user: bool = True   # FE luôn gửi true nếu người dùng đã chỉnh sửa dù chỉ 1 câu

class QuizQuestionOut(QuizQuestionIn):
    id: UUID
    order_index: int

class QuizOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    total_questions: int
    is_edited_by_user: bool
    questions: list[QuizQuestionOut]
```

### 6.2 Backend — Endpoint lưu & lấy quiz (`api/routes/quizzes.py`)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from app.api.deps import get_db, get_current_user
from app.db.models import Quiz, QuizQuestion
from app.schemas.quiz import QuizCreateRequest, QuizOut

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])

@router.post("", response_model=QuizOut)
async def create_quiz(
    payload: QuizCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not payload.questions:
        raise HTTPException(400, "Quiz phải có ít nhất 1 câu hỏi")

    quiz = Quiz(
        id=uuid4(),
        library_id=payload.library_id,
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        total_questions=len(payload.questions),
        is_edited_by_user=payload.is_edited_by_user,
    )
    db.add(quiz)
    await db.flush()   # có quiz.id để gán FK cho các câu hỏi

    for idx, q in enumerate(payload.questions):
        db.add(QuizQuestion(
            id=uuid4(),
            quiz_id=quiz.id,
            order_index=idx,
            question_text=q.question_text,
            option_a=q.option_a, option_b=q.option_b,
            option_c=q.option_c, option_d=q.option_d,
            correct_answer=q.correct_answer,
            explanation=q.explanation,
            source_page=q.source_page,
        ))
    await db.commit()
    await db.refresh(quiz)
    return await _to_quiz_out(db, quiz)


@router.get("/{quiz_id}", response_model=QuizOut)
async def get_quiz(quiz_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    quiz = await db.get(Quiz, quiz_id)
    if not quiz or quiz.user_id != current_user.id:
        raise HTTPException(404, "Không tìm thấy quiz")
    return await _to_quiz_out(db, quiz)


@router.put("/{quiz_id}", response_model=QuizOut)
async def update_quiz(quiz_id: str, payload: QuizCreateRequest, db: AsyncSession = Depends(get_db),
                       current_user=Depends(get_current_user)):
    """Cho phép sửa lại quiz đã lưu trước đó (mở lại Quiz Editor từ lịch sử)."""
    quiz = await db.get(Quiz, quiz_id)
    if not quiz or quiz.user_id != current_user.id:
        raise HTTPException(404, "Không tìm thấy quiz")

    await db.execute(QuizQuestion.__table__.delete().where(QuizQuestion.quiz_id == quiz_id))
    quiz.title = payload.title
    quiz.description = payload.description
    quiz.total_questions = len(payload.questions)
    quiz.is_edited_by_user = True
    for idx, q in enumerate(payload.questions):
        db.add(QuizQuestion(id=uuid4(), quiz_id=quiz.id, order_index=idx, **q.model_dump(exclude={"correct_answer"}),
                             correct_answer=q.correct_answer))
    await db.commit()
    return await _to_quiz_out(db, quiz)


async def _to_quiz_out(db: AsyncSession, quiz: Quiz) -> QuizOut:
    result = await db.execute(
        select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.order_index)
    )
    questions = result.scalars().all()
    return QuizOut(
        id=quiz.id, title=quiz.title, description=quiz.description,
        total_questions=quiz.total_questions, is_edited_by_user=quiz.is_edited_by_user,
        questions=questions,
    )
```

### 6.3 Frontend — `QuizEditorCard.tsx` (sửa từng câu, thêm/xóa câu, lưu)

```tsx
// components/quiz/QuizEditorCard.tsx
import { useState } from "react";
import { api } from "@/lib/api";

type Question = {
  question_text: string;
  option_a: string; option_b: string; option_c: string; option_d: string;
  correct_answer: "A" | "B" | "C" | "D";
  explanation?: string;
  source_page?: number;
};

export function QuizEditorCard({
  libraryId,
  initialQuestions,
  suggestedTitle,
}: {
  libraryId: string;
  initialQuestions: Question[];
  suggestedTitle: string;
}) {
  const [title, setTitle] = useState(suggestedTitle);
  const [questions, setQuestions] = useState<Question[]>(initialQuestions);
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const updateField = (idx: number, field: keyof Question, value: string) => {
    setQuestions((prev) =>
      prev.map((q, i) => (i === idx ? { ...q, [field]: value } : q))
    );
  };

  const removeQuestion = (idx: number) =>
    setQuestions((prev) => prev.filter((_, i) => i !== idx));

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const { data } = await api.post("/api/quizzes", {
        library_id: libraryId,
        title,
        questions,
        is_edited_by_user: true,
      });
      setSavedId(data.id);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Lưu quiz thất bại, thử lại sau.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="quiz-editor-card">
      <input
        className="quiz-title-input"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Tên bộ đề"
      />

      {questions.map((q, idx) => (
        <div key={idx} className="quiz-question-block">
          <div className="quiz-question-header">
            <span>Câu {idx + 1}</span>
            <button onClick={() => removeQuestion(idx)}>Xóa</button>
          </div>

          <textarea
            value={q.question_text}
            onChange={(e) => updateField(idx, "question_text", e.target.value)}
          />

          {(["A", "B", "C", "D"] as const).map((letter) => {
            const field = `option_${letter.toLowerCase()}` as keyof Question;
            return (
              <label key={letter} className="quiz-option-row">
                <input
                  type="radio"
                  name={`correct-${idx}`}
                  checked={q.correct_answer === letter}
                  onChange={() => updateField(idx, "correct_answer", letter)}
                />
                <span>{letter}.</span>
                <input
                  value={q[field] as string}
                  onChange={(e) => updateField(idx, field, e.target.value)}
                />
              </label>
            );
          })}

          <textarea
            className="quiz-explanation"
            placeholder="Giải thích đáp án"
            value={q.explanation ?? ""}
            onChange={(e) => updateField(idx, "explanation", e.target.value)}
          />
        </div>
      ))}

      <div className="quiz-editor-actions">
        <button disabled={saving} onClick={handleSave}>
          {saving ? "Đang lưu..." : "Lưu vào Database"}
        </button>
        {savedId && <span className="quiz-saved-note">Đã lưu ✓ (ID: {savedId})</span>}
        {error && <span className="quiz-error-note">{error}</span>}
      </div>
    </div>
  );
}
```

### 6.4 Nối vào ChatWindow — hiện Preview trước, mở Editor khi bấm "Chỉnh sửa"

```tsx
// components/chat/ChatWindow.tsx
import { CopilotChat } from "@copilotkit/react-ui";
import { useCoAgentStateRender } from "@copilotkit/react-core";
import { useState } from "react";
import { QuizPreviewCard } from "../quiz/QuizPreviewCard";
import { QuizEditorCard } from "../quiz/QuizEditorCard";

export function ChatWindow({ libraryId }: { libraryId: string }) {
  const [editing, setEditing] = useState(false);

  useCoAgentStateRender({
    name: "assistant",
    render: ({ state }) => {
      if (!state.quiz_draft?.length) return null;
      return editing ? (
        <QuizEditorCard
          libraryId={libraryId}
          initialQuestions={state.quiz_draft}
          suggestedTitle={`Đề ôn tập ${new Date().toLocaleDateString("vi-VN")}`}
        />
      ) : (
        <QuizPreviewCard questions={state.quiz_draft} onEdit={() => setEditing(true)} />
      );
    },
  });

  return <CopilotChat agent="assistant" labels={{ title: "Trợ lý Thư viện" }} />;
}
```

> `QuizPreviewCard` chỉ hiển thị danh sách câu hỏi read-only + nút "Chỉnh sửa"; khi bấm, `editing=true` chuyển sang `QuizEditorCard` cho sửa trực tiếp như mô tả ở mục 6.3. Sau khi `handleSave` thành công, có thể thêm nút "Xuất PDF" gọi `QuizPdfExport.tsx` (client-side, dùng dữ liệu vừa lưu, không qua LangGraph).

---

## 7. Danh sách API Endpoints

| Method | Path | Chức năng |
|---|---|---|
| POST | `/api/auth/register`, `/login` | Xác thực JWT |
| GET/POST | `/api/libraries` | CRUD Thư viện |
| GET/POST | `/api/libraries/{id}/sessions` | CRUD đoạn chat |
| POST | `/api/documents/upload` | Upload PDF → MinIO → `ingestion_jobs` |
| GET | `/api/documents/{id}/progress` | Poll tiến độ ingest |
| POST | `/api/copilotkit` | Endpoint DUY NHẤT cho chatbot (chat + sinh đề) |
| POST | `/api/quizzes` | ⭐ Lưu quiz mới sau khi chỉnh sửa (từ `quiz_draft`) |
| GET | `/api/quizzes/{id}` | ⭐ Lấy chi tiết quiz đã lưu (để export PDF / mở lại Editor) |
| PUT | `/api/quizzes/{id}` | ⭐ Cập nhật quiz đã lưu trước đó |

---

## 8. Luồng End-to-End (đầy đủ, gồm cả bước lưu)

```
User: "Tạo 40 câu trắc nghiệm chương Subnet"
  → CopilotKit gửi kèm headers (model/key) tới /api/copilotkit, thread_id = session_id
  → agent_node (bind_tools) quyết định gọi generate_quiz(num_questions=40, focus_topic="Subnet")
  → ToolNode chạy generate_quiz → quiz_subgraph.invoke(...)
       init → (generator[Groq] → evaluator[Gemini] → [reflection nếu bị từ chối] → synthesizer[Gemini]) × ceil(40/18) batch
  → Command cập nhật state.quiz_draft (40 câu) → quay lại agent_node xác nhận hoàn tất
  → Frontend: useCoAgentStateRender phát hiện quiz_draft → hiện QuizPreviewCard
  → User bấm "Chỉnh sửa" → QuizEditorCard cho sửa câu hỏi/đáp án trực tiếp
  → User bấm "Lưu vào Database" → POST /api/quizzes → ghi bảng quizzes + quiz_questions
      (is_edited_by_user=true nếu có chỉnh sửa)
  → User bấm "Xuất PDF" → GET /api/quizzes/{id} → render client-side 2 bản (Đề thi/Đáp án)
```

---

## 9. Thứ tự triển khai đề xuất

1. Chạy DDL mục 2, seed thử 1 user + 1 library.
2. Viết `vector_store.py` (similarity_search) + `llm_factory.py`, test độc lập bằng script Python.
3. Viết `quiz_subgraph` (3 node + batching), test với `num_questions=5, batch_size=5` trước khi thử batch thật.
4. Ghép `agent_node` + `ToolNode` thành `build_assistant_graph`, test bằng `graph.invoke()` CLI (chưa cần CopilotKit).
5. Thêm `AsyncPostgresSaver`, test resume giữa chừng.
6. Mount `/api/copilotkit`, test qua CopilotKit Playground.
7. Build `ChatWindow` + `QuizPreviewCard` + `QuizEditorCard`, cuối cùng nối `POST /api/quizzes`.
8. Thêm `QuizPdfExport.tsx` (2 bản PDF) sau khi luồng lưu đã chạy ổn.

---

**Còn thiếu / có thể viết tiếp nếu bạn cần:** code đầy đủ 3 node `generator_node.py` / `evaluator_node.py` / `synthesizer_node.py` khớp `QuizState` mới, `QuizPreviewCard.tsx`, hoặc `QuizPdfExport.tsx` (2 bản PDF Đề thi/Đáp án bằng `@react-pdf/renderer`).
