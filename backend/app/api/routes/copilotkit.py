"""
CopilotKit endpoint — registers the single LangGraph agent (V2 Architecture).
"""

from fastapi import FastAPI

def register_copilotkit(app: FastAPI, checkpointer=None):
    """
    Register the CopilotKit v2 endpoint with the FastAPI app.
    Mounts a single LangGraph agent named "assistant".
    """
    from copilotkit import CopilotKitRemoteEndpoint
    from copilotkit.integrations.fastapi import add_fastapi_endpoint
    from app.agents.assistant.graph import build_assistant_graph

    try:
        from copilotkit import LangGraphAGUIAgent as CopilotAgent
    except ImportError:
        from copilotkit import LangGraphAgent as CopilotAgent

    sdk = CopilotKitRemoteEndpoint(
        agents=[
            CopilotAgent(
                name="assistant",
                description=(
                    "Trợ lý Thư viện: trả lời câu hỏi dựa trên tài liệu "
                    "và tự tạo đề trắc nghiệm khi được yêu cầu"
                ),
                graph=build_assistant_graph(checkpointer),
            )
        ]
    )

    # Hỗ trợ GET /info vì Frontend (v1.x) dùng GET nhưng Backend cũ mặc định chỉ hỗ trợ POST
    @app.get("/api/copilotkit/info")
    async def copilotkit_info_get():
        return sdk.info(context={"properties": {}, "frontend_url": None})

    add_fastapi_endpoint(app, sdk, "/api/copilotkit")
