"""
CopilotKit endpoint — registers the single LangGraph agent.
"""

from fastapi import FastAPI


def register_copilotkit(app: FastAPI, checkpointer=None):
    """
    Register the CopilotKit endpoint with the FastAPI app.
    Mounts a single LangGraphAgent named "assistant".
    """
    from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
    from copilotkit.integrations.fastapi import add_fastapi_endpoint
    from app.agents.assistant.graph import build_assistant_graph

    sdk = CopilotKitRemoteEndpoint(
        agents=[
            LangGraphAgent(
                name="assistant",
                description=(
                    "Trợ lý Thư viện: trả lời câu hỏi dựa trên tài liệu "
                    "và tự tạo đề trắc nghiệm khi được yêu cầu"
                ),
                graph=build_assistant_graph(checkpointer),
            )
        ]
    )
    add_fastapi_endpoint(app, sdk, "/api/copilotkit")
