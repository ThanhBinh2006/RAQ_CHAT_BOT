"""
CopilotKit endpoint — registers the single LangGraph agent (V2 Architecture).
"""

from fastapi import FastAPI

def register_copilotkit(app: FastAPI, checkpointer=None):
    """
    Register the CopilotKit v2 endpoint with the FastAPI app.
    Mounts a single LangGraph agent named "assistant".
    """
    # 💡 V2 sử dụng CopilotRuntime thay vì CopilotKitRemoteEndpoint
    from copilotkit import CopilotRuntime 
    from copilotkit.integrations.fastapi import add_fastapi_endpoint
    from app.agents.assistant.graph import build_assistant_graph

    # Import class Agent bọc LangGraph theo đúng phiên bản thư viện bạn đang cài
    try:
        from copilotkit import LangGraphAGUIAgent as CopilotAgent
    except ImportError:
        from copilotkit import LangGraphAgent as CopilotAgent

    # 1. Khởi tạo CopilotRuntime bản v2
    runtime = CopilotRuntime()

    # 2. Đăng ký Agent "assistant" vào hệ thống Runtime mới
    agent_instance = CopilotAgent(
        name="assistant",
        description=(
            "Trợ lý Thư viện: trả lời câu hỏi dựa trên tài liệu "
            "và tự tạo đề trắc nghiệm khi được yêu cầu"
        ),
        graph=build_assistant_graph(checkpointer),
    )
    runtime.add_agent(agent_instance)

    # 3. Tích hợp endpoint vào FastAPI (Hỗ trợ toàn bộ các route GET/POST /info và /stream tự động)
    add_fastapi_endpoint(app, runtime, path="/api/copilotkit")
