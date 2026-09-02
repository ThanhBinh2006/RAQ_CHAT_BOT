import pytest
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.assistant.graph import build_assistant_graph
from app.agents.assistant.state import AgentState

@pytest.mark.asyncio
async def test_assistant_graph_invoke():
    """
    Test the core logic of the LangGraph assistant graph.
    This simulates how the agent processes an incoming message without touching the API.
    Because USE_MOCK_LLM=true in pytest.ini, this will use the MockChatModel.
    """
    # 1. Khởi tạo đồ thị
    graph = build_assistant_graph()
    
    # 2. Chuẩn bị state đầu vào
    initial_state: AgentState = {
        "messages": [HumanMessage(content="Xin chào, rag là gì?")],
        "user_id": "test_user",
        "library_id": "test_lib",
        "session_id": "test_session",
        "model_config": {
            "supervisor": "gemini-2.5-flash",
            "generator": "gemini-1.5-flash-8b",
            "evaluator": "gemini-2.5-flash",
            "synthesizer": "gemini-1.5-flash-8b"
        },
        "api_keys": {},
        "citations": [],
        "quiz_draft": None
    }
    
    # 3. Chạy đồ thị
    result_state = await graph.ainvoke(initial_state)
    
    # 4. Kiểm tra kết quả
    assert "messages" in result_state
    
    messages = result_state["messages"]
    assert len(messages) >= 2 # Ít nhất gồm 1 câu hỏi (Human) và 1 câu trả lời (AI)
    
    # Lấy tin nhắn cuối cùng (phải là AIMessage từ MockChatModel)
    last_message = messages[-1]
    print(f"\n\nHuman: {initial_state["messages"][0].content}")
    print(f"AI: {last_message.content}")
    assert isinstance(last_message, AIMessage)
    # assert "chế độ mock" in last_message.content or "mock" in last_message.content.lower()
